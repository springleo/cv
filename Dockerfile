# Use nginx as the base image to serve static HTML
FROM nginx:alpine

# Copy the entire project to nginx's default serving directory
COPY . /usr/share/nginx/html/

# Create a startup script that configures nginx to listen on the PORT environment variable
RUN mkdir -p /app && \
    echo '#!/bin/sh\n\
PORT=${PORT:-8080}\n\
sed -i "s/listen 80;/listen $PORT;/" /etc/nginx/conf.d/default.conf\n\
nginx -g "daemon off;"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Expose the PORT (Cloud Run will use 8080 by default)
EXPOSE 8080

# Set the startup script as entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
