FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Run in development mode
CMD ["npm", "run", "dev"]
