FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["/bin/sh", "-c", "export PORT=\"${PORT:-80}\" && export BACKEND_URL=\"${BACKEND_URL:-http://backend:8000}\" && export RESOLVER=\"$(awk 'BEGIN{ORS=\" \"} $1==\"nameserver\" {print $2}' /etc/resolv.conf)\" && if [ -z \"$RESOLVER\" ]; then export RESOLVER=\"127.0.0.11\"; fi && envsubst '$PORT $BACKEND_URL $RESOLVER' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
