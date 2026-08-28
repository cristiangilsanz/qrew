FROM node:22-alpine AS builder

WORKDIR /repo

COPY package.json package-lock.json ./
COPY apps/app/package.json apps/app/package.json

RUN npm ci --include-workspace-root -w apps/app

COPY apps/app apps/app

ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build -w apps/app

FROM nginx:alpine AS runtime

COPY --from=builder /repo/apps/app/dist /usr/share/nginx/html

COPY apps/app/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
