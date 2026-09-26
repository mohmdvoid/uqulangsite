# Self-hosting image: build the site with Python, serve it with nginx.
# Only the deployment directory reaches the final image.

FROM python:3.12-slim AS build
WORKDIR /src

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt brotli

COPY . .
RUN python3 tools/build.py --check \
 && python3 tools/check_links.py \
 && python3 tools/postprocess.py

FROM nginx:1.27-alpine
COPY --from=build /src/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://localhost/ >/dev/null || exit 1

EXPOSE 80
