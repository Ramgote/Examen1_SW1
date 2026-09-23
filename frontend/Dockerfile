FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Se especifica --host para permitir que Docker exponga el puerto a tu máquina Windows
CMD ["npm", "run", "dev", "--", "--host"]
