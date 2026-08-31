FROM node:20-alpine

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund --network-timeout 600000

COPY frontend ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
