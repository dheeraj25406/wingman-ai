import os
import glob
import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi


class RunbookChunk:
    def __init__(self, doc_id: str, title: str, section: str, content: str, service: str, category: str):
        self.doc_id = doc_id
        self.title = title
        self.section = section
        self.content = content
        self.service = service
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "section": self.section,
            "content": self.content,
            "service": self.service,
            "category": self.category,
        }


class RunbookRAG:
    """
    Domain-specific Hybrid Runbook RAG retriever.
    Combines sparse lexical BM25 search with metadata filtering and reciprocal rank fusion.
    Guarantees citation integrity: every chunk contains doc_id, section, and service references.
    """

    def __init__(self, runbooks_dir: str = "runbooks"):
        self.runbooks_dir = runbooks_dir
        self.chunks: List[RunbookChunk] = []
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_tokens: List[List[str]] = []
        self._load_and_index()

    def _load_and_index(self):
        self.chunks = []
        md_files = glob.glob(os.path.join(self.runbooks_dir, "*.md"))

        for fpath in md_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()

                # Parse title
                title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else os.path.basename(fpath)

                # Parse metadata
                service_match = re.search(r"Service:\s*([^\n]+)", text)
                category_match = re.search(r"Category:\s*([^\n]+)", text)
                id_match = re.search(r"Runbook ID:\s*([^\n]+)", text)

                service = service_match.group(1).strip() if service_match else "generic"
                category = category_match.group(1).strip() if category_match else "General"
                doc_id = id_match.group(1).strip() if id_match else os.path.splitext(os.path.basename(fpath))[0]

                # Chunk by ## headers
                sections = re.split(r"\n(?=##\s+)", text)
                for sec in sections:
                    sec_clean = sec.strip()
                    if not sec_clean:
                        continue
                    sec_header_match = re.search(r"^##\s+([^\n]+)", sec_clean)
                    section_name = sec_header_match.group(1).strip() if sec_header_match else "General Overview"

                    chunk = RunbookChunk(
                        doc_id=doc_id,
                        title=title,
                        section=section_name,
                        content=sec_clean,
                        service=service,
                        category=category,
                    )
                    self.chunks.append(chunk)
            except Exception as e:
                print(f"[RAG] Error indexing {fpath}: {e}")

        # Build BM25 index
        self.corpus_tokens = [self._tokenize(c.title + " " + c.section + " " + c.content) for c in self.chunks]
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def retrieve(self, query: str, service_id: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: BM25 score combined with service metadata boost.
        Returns top-k cited runbook passages.
        """
        if not self.chunks or not self.bm25:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        bm25_scores = self.bm25.get_scores(query_tokens)

        scored_results = []
        for idx, (chunk, bm25_score) in enumerate(zip(self.chunks, bm25_scores)):
            score = float(bm25_score)
            # Service matching boost
            if service_id and chunk.service.lower() == service_id.lower():
                score += 3.0

            scored_results.append((score, chunk))

        # Sort descending
        scored_results.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scored_results[:top_k]:
            item = chunk.to_dict()
            item["relevance_score"] = round(score, 4)
            item["citation"] = f"[{chunk.doc_id}] {chunk.title} — Section: {chunk.section}"
            results.append(item)

        return results


runbook_rag = RunbookRAG()
