import asyncio
import time
import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from simulator.faults.fault_engine import fault_engine
from simulator.telemetry.buffer import (
    telemetry_buffer,
    ServiceMetricPoint,
    LogRecord,
    SpanRecord,
)


class ServiceMesh:
    """
    Simulates the distributed e-commerce application runtime.
    Executes real asynchronous HTTP-style request pipelines across:
    API Gateway -> [User, Product, Checkout] -> [Payment, Order] -> [Database]
    """

    SERVICE_BASELINES = {
        "api-gateway": {
            "cpu": 18.0, "memory": 28.0, "latency_p50": 12.0, "latency_p95": 28.0, "latency_p99": 45.0,
            "db_conn": 0.0, "queue": 5.0
        },
        "user-service": {
            "cpu": 15.0, "memory": 35.0, "latency_p50": 8.0, "latency_p95": 20.0, "latency_p99": 35.0,
            "db_conn": 12.0, "queue": 2.0
        },
        "product-service": {
            "cpu": 22.0, "memory": 40.0, "latency_p50": 15.0, "latency_p95": 32.0, "latency_p99": 50.0,
            "db_conn": 18.0, "queue": 8.0
        },
        "checkout-service": {
            "cpu": 25.0, "memory": 38.0, "latency_p50": 30.0, "latency_p95": 65.0, "latency_p99": 95.0,
            "db_conn": 10.0, "queue": 15.0
        },
        "payment-service": {
            "cpu": 19.0, "memory": 30.0, "latency_p50": 45.0, "latency_p95": 90.0, "latency_p99": 140.0,
            "db_conn": 5.0, "queue": 4.0
        },
        "order-service": {
            "cpu": 24.0, "memory": 42.0, "latency_p50": 35.0, "latency_p95": 70.0, "latency_p99": 110.0,
            "db_conn": 22.0, "queue": 20.0
        },
    }

    def __init__(self):
        self._running = False
        self._traffic_task: Optional[asyncio.Task] = None
        self._metric_task: Optional[asyncio.Task] = None
        self._target_rps = 10.0
        self._request_counter = 0

    async def start(self):
        if self._running:
            return
        self._running = True
        self._traffic_task = asyncio.create_task(self._traffic_loop())
        self._metric_task = asyncio.create_task(self._metric_collector_loop())

    async def stop(self):
        self._running = False
        if self._traffic_task:
            self._traffic_task.cancel()
        if self._metric_task:
            self._metric_task.cancel()

    def set_traffic_rps(self, rps: float):
        self._target_rps = max(1.0, min(100.0, rps))

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def target_rps(self) -> float:
        return self._target_rps

    # --------------------------------------------------------------------------
    # Traffic Generation Loop
    # --------------------------------------------------------------------------
    async def _traffic_loop(self):
        while self._running:
            try:
                # Interval based on target RPS
                interval = 1.0 / self._target_rps
                await self._execute_synthetic_request()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.1)

    async def _execute_synthetic_request(self):
        trace_id = f"tr-{uuid.uuid4().hex[:16]}"
        self._request_counter += 1
        req_type = random.choices(["checkout", "product_catalog", "user_auth"], weights=[0.45, 0.40, 0.15])[0]

        start_time = time.time()
        root_span_id = f"sp-{uuid.uuid4().hex[:8]}"

        if req_type == "checkout":
            await self._flow_checkout(trace_id, root_span_id, start_time)
        elif req_type == "product_catalog":
            await self._flow_products(trace_id, root_span_id, start_time)
        else:
            await self._flow_user(trace_id, root_span_id, start_time)

    # --------------------------------------------------------------------------
    # Request Flows
    # --------------------------------------------------------------------------
    async def _flow_checkout(self, trace_id: str, root_span_id: str, start_time: float):
        # 1. API Gateway Span
        gateway_span = SpanRecord(
            trace_id=trace_id,
            span_id=root_span_id,
            parent_span_id=None,
            service_id="api-gateway",
            operation="POST /api/v1/checkout",
            start_time=start_time,
            duration_ms=0.0,
            status="OK",
            http_status=200,
        )

        checkout_span_id = f"sp-{uuid.uuid4().hex[:8]}"
        checkout_fault = fault_engine.get_fault_for_service("checkout-service")
        cpu_fault = fault_engine.get_fault_for_service("checkout-service") if checkout_fault and checkout_fault.fault_type == "cpu_saturation" else None

        checkout_delay = random.uniform(15.0, 30.0)
        if cpu_fault:
            checkout_delay += 1200.0 * cpu_fault.intensity

        # 2. Checkout -> Payment
        payment_span_id = f"sp-{uuid.uuid4().hex[:8]}"
        payment_fault = fault_engine.get_fault_for_service("payment-service")
        payment_status = "OK"
        payment_http = 200
        payment_err = None
        payment_delay = random.uniform(20.0, 45.0)

        if payment_fault:
            if payment_fault.fault_type == "downstream_latency":
                payment_delay += 3500.0 * payment_fault.intensity
            elif payment_fault.fault_type == "downstream_failure":
                if random.random() < payment_fault.intensity:
                    payment_status = "ERROR"
                    payment_http = 503
                    payment_err = "PaymentGatewayUnavailableException: 3rd-party acquirer connection refused"

        telemetry_buffer.record_span(SpanRecord(
            trace_id=trace_id,
            span_id=payment_span_id,
            parent_span_id=checkout_span_id,
            service_id="payment-service",
            operation="POST /payments/charge",
            start_time=time.time(),
            duration_ms=payment_delay,
            status=payment_status,
            http_status=payment_http,
            error_message=payment_err,
        ))

        if payment_status == "ERROR":
            telemetry_buffer.record_log(LogRecord(
                id=f"log-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                epoch=time.time(),
                service_id="payment-service",
                level="ERROR",
                message=payment_err,
                trace_id=trace_id,
                span_id=payment_span_id,
                error_type="PaymentGatewayUnavailableException",
            ))

        # 3. Checkout -> Order Service -> DB
        order_span_id = f"sp-{uuid.uuid4().hex[:8]}"
        order_fault = fault_engine.get_fault_for_service("order-service")
        order_status = "OK"
        order_http = 200
        order_err = None
        order_delay = random.uniform(15.0, 35.0)

        if order_fault:
            if order_fault.fault_type == "db_pool_exhaustion":
                if random.random() < order_fault.intensity:
                    order_status = "ERROR"
                    order_http = 500
                    order_delay += 2500.0
                    order_err = "ConnectionPoolTimeoutError: Timeout acquiring PostgreSQL connection after 2500ms (pool exhausted: 100/100 active)"
            elif order_fault.fault_type == "queue_backlog":
                order_delay += 800.0 * order_fault.intensity

        telemetry_buffer.record_span(SpanRecord(
            trace_id=trace_id,
            span_id=order_span_id,
            parent_span_id=checkout_span_id,
            service_id="order-service",
            operation="POST /orders/create",
            start_time=time.time(),
            duration_ms=order_delay,
            status=order_status,
            http_status=order_http,
            error_message=order_err,
        ))

        if order_status == "ERROR":
            telemetry_buffer.record_log(LogRecord(
                id=f"log-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                epoch=time.time(),
                service_id="order-service",
                level="ERROR",
                message=order_err,
                trace_id=trace_id,
                span_id=order_span_id,
                error_type="ConnectionPoolTimeoutError",
                details={"active_connections": 100, "max_connections": 100, "wait_queue": 42}
            ))

        # Overall checkout status propagation
        overall_checkout_status = "OK"
        overall_http = 200
        checkout_err_msg = None

        if payment_status == "ERROR":
            overall_checkout_status = "ERROR"
            overall_http = 502
            checkout_err_msg = "BadGateway: Failed downstream payment charge"
        elif order_status == "ERROR":
            overall_checkout_status = "ERROR"
            overall_http = 500
            checkout_err_msg = "InternalServerError: Order fulfillment transaction failed"

        total_checkout_duration = checkout_delay + payment_delay + order_delay

        telemetry_buffer.record_span(SpanRecord(
            trace_id=trace_id,
            span_id=checkout_span_id,
            parent_span_id=root_span_id,
            service_id="checkout-service",
            operation="POST /checkout/process",
            start_time=start_time,
            duration_ms=total_checkout_duration,
            status=overall_checkout_status,
            http_status=overall_http,
            error_message=checkout_err_msg,
        ))

        if overall_checkout_status == "ERROR":
            telemetry_buffer.record_log(LogRecord(
                id=f"log-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                epoch=time.time(),
                service_id="checkout-service",
                level="ERROR",
                message=checkout_err_msg,
                trace_id=trace_id,
                span_id=checkout_span_id,
            ))

        # Final Gateway record
        gateway_span.duration_ms = total_checkout_duration + random.uniform(5.0, 10.0)
        gateway_span.status = overall_checkout_status
        gateway_span.http_status = overall_http
        gateway_span.error_message = checkout_err_msg
        telemetry_buffer.record_span(gateway_span)

    async def _flow_products(self, trace_id: str, root_span_id: str, start_time: float):
        prod_span_id = f"sp-{uuid.uuid4().hex[:8]}"
        prod_fault = fault_engine.get_fault_for_service("product-service")
        prod_status = "OK"
        prod_http = 200
        prod_err = None
        duration = random.uniform(15.0, 35.0)

        if prod_fault and prod_fault.fault_type == "memory_pressure":
            duration += 1500.0 * prod_fault.intensity
            if random.random() < 0.4 * prod_fault.intensity:
                prod_status = "ERROR"
                prod_http = 500
                prod_err = "OutOfMemoryError: Java heap space exceeded in cache indexer"

        telemetry_buffer.record_span(SpanRecord(
            trace_id=trace_id,
            span_id=prod_span_id,
            parent_span_id=root_span_id,
            service_id="product-service",
            operation="GET /products/catalog",
            start_time=start_time,
            duration_ms=duration,
            status=prod_status,
            http_status=prod_http,
            error_message=prod_err,
        ))

        if prod_status == "ERROR":
            telemetry_buffer.record_log(LogRecord(
                id=f"log-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                epoch=time.time(),
                service_id="product-service",
                level="ERROR",
                message=prod_err,
                trace_id=trace_id,
                span_id=prod_span_id,
                error_type="OutOfMemoryError",
            ))

        # Root gateway span
        telemetry_buffer.record_span(SpanRecord(
            trace_id=trace_id,
            span_id=root_span_id,
            parent_span_id=None,
            service_id="api-gateway",
            operation="GET /api/v1/products",
            start_time=start_time,
            duration_ms=duration + random.uniform(4.0, 8.0),
            status=prod_status,
            http_status=prod_http,
            error_message=prod_err,
        ))

    async def _flow_user(self, trace_id: str, root_span_id: str, start_time: float):
        user_span_id = f"sp-{uuid.uuid4().hex[:8]}"
        user_fault = fault_engine.get_fault_for_service("user-service")
        user_status = "OK"
        user_http = 200
        user_err = None
        duration = random.uniform(8.0, 20.0)

        if user_fault and user_fault.fault_type == "bad_deployment":
            if random.random() < user_fault.intensity:
                user_status = "ERROR"
                user_http = 500
                user_err = "KeyError: 'JWT_SECRET_KEY' configuration missing in release v2.4.1"

        telemetry_buffer.record_span(SpanRecord(
            trace_id=trace_id,
            span_id=user_span_id,
            parent_span_id=root_span_id,
            service_id="user-service",
            operation="POST /users/auth/verify",
            start_time=start_time,
            duration_ms=duration,
            status=user_status,
            http_status=user_http,
            error_message=user_err,
        ))

        if user_status == "ERROR":
            telemetry_buffer.record_log(LogRecord(
                id=f"log-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                epoch=time.time(),
                service_id="user-service",
                level="ERROR",
                message=user_err,
                trace_id=trace_id,
                span_id=user_span_id,
                error_type="KeyError",
            ))

        telemetry_buffer.record_span(SpanRecord(
            trace_id=trace_id,
            span_id=root_span_id,
            parent_span_id=None,
            service_id="api-gateway",
            operation="POST /api/v1/auth",
            start_time=start_time,
            duration_ms=duration + random.uniform(3.0, 6.0),
            status=user_status,
            http_status=user_http,
            error_message=user_err,
        ))

    # --------------------------------------------------------------------------
    # Telemetry Sampling & Aggregation Loop (Every 5 seconds)
    # --------------------------------------------------------------------------
    async def _metric_collector_loop(self):
        while self._running:
            try:
                now_epoch = time.time()
                iso_time = datetime.now(timezone.utc).isoformat()

                for service_id, baseline in self.SERVICE_BASELINES.items():
                    active_fault = fault_engine.get_fault_for_service(service_id)

                    # Compute dynamic variations
                    cpu = baseline["cpu"] + random.uniform(-2.0, 2.0)
                    mem = baseline["memory"] + random.uniform(-1.0, 1.0)
                    req_rate = self._target_rps * random.uniform(0.9, 1.1)
                    err_rate = random.uniform(0.001, 0.005)
                    p50 = baseline["latency_p50"] + random.uniform(-2.0, 2.0)
                    p95 = baseline["latency_p95"] + random.uniform(-3.0, 3.0)
                    p99 = baseline["latency_p99"] + random.uniform(-5.0, 5.0)
                    db_conn = baseline["db_conn"] + random.uniform(-2.0, 2.0)
                    queue = baseline["queue"] + random.uniform(-1.0, 1.0)
                    timeout_rate = 0.0

                    # Apply active faults to metrics
                    if active_fault:
                        intensity = active_fault.intensity
                        if active_fault.fault_type == "db_pool_exhaustion":
                            db_conn = 98.0 + random.uniform(0.0, 2.0)
                            err_rate = 0.65 * intensity
                            p95 = 2800.0 * intensity
                            p99 = 3500.0 * intensity
                            timeout_rate = 0.45 * intensity
                        elif active_fault.fault_type == "cpu_saturation":
                            cpu = 95.0 + random.uniform(0.0, 4.5)
                            p95 = 1400.0 * intensity
                            p99 = 2200.0 * intensity
                        elif active_fault.fault_type == "memory_pressure":
                            mem = 94.0 + random.uniform(0.0, 5.0)
                            p95 = 1100.0 * intensity
                            err_rate = 0.25 * intensity
                        elif active_fault.fault_type == "downstream_latency":
                            p50 = 1800.0 * intensity
                            p95 = 3800.0 * intensity
                            p99 = 4500.0 * intensity
                            timeout_rate = 0.35 * intensity
                        elif active_fault.fault_type == "downstream_failure":
                            err_rate = 0.85 * intensity
                        elif active_fault.fault_type == "queue_backlog":
                            queue = 12500.0 * intensity
                            p95 = 950.0 * intensity
                        elif active_fault.fault_type == "bad_deployment":
                            err_rate = 0.90 * intensity

                    # Constrain ranges
                    metric_point = ServiceMetricPoint(
                        timestamp=iso_time,
                        epoch=now_epoch,
                        service_id=service_id,
                        cpu_utilization=round(max(1.0, min(100.0, cpu)), 2),
                        memory_utilization=round(max(1.0, min(100.0, mem)), 2),
                        request_rate=round(req_rate, 2),
                        error_rate=round(max(0.0, min(1.0, err_rate)), 4),
                        latency_p50=round(max(1.0, p50), 2),
                        latency_p95=round(max(2.0, p95), 2),
                        latency_p99=round(max(5.0, p99), 2),
                        db_connections=round(max(0.0, min(100.0, db_conn)), 2),
                        queue_depth=round(max(0.0, queue), 2),
                        timeout_rate=round(max(0.0, min(1.0, timeout_rate)), 4),
                    )
                    telemetry_buffer.record_metric(metric_point)

                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5.0)


# Global Singleton
service_mesh = ServiceMesh()
