# frontend/Dockerfile

# 1. Base image
FROM node:20-alpine

# 2. Set working directory
WORKDIR /app

# 3. Copy package files first (better caching)
COPY package.json package-lock.json* ./

# 4. Install dependencies
RUN npm ci

# 5. Copy the rest of the code
COPY . .

# 6. Build the Next.js app (optional for dev, but good practice)
# RUN npm run build 
# (We skip build in dev mode to keep startup fast)

# 7. Expose the port
EXPOSE 3000

# 8. Start the app
CMD ["npm", "run", "dev"]