FROM node:18-alpine

WORKDIR /app

# Устанавливаем зависимости
COPY package*.json ./
RUN npm install

# Копируем исходники
COPY . .

# Открываем порт
EXPOSE 3000

# Запускаем в режиме разработки
CMD ["npm", "run", "dev"]