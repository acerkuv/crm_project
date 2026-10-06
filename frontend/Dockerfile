FROM node:20-alpine

WORKDIR /app

# Устанавливаем зависимости
COPY package*.json ./
RUN npm install

# Устанавливаем PWA плагин
RUN npm install -D vite-plugin-pwa

# Копируем исходники
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
