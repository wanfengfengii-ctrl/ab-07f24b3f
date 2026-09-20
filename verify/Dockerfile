FROM node:22-bookworm

WORKDIR /verify

COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund \
    && npx playwright install --with-deps chromium

COPY . .

# The acceptance runner is the container's executable entry point.
ENTRYPOINT ["node", "acceptance.mjs"]
