FROM mcr.microsoft.com/playwright:v1.48.2-jammy

WORKDIR /verify

# 基础镜像已内置与 playwright@1.48.2 匹配的浏览器，跳过重复下载
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY verify.js ./

CMD ["node", "verify.js"]
