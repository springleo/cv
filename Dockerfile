# Use nginx as the base image to serve static HTML
FROM nginx:alpine

# Copy the entire project to nginx's default serving directory
COPY . /usr/share/nginx/html/

# Expose port 80
EXPOSE 80

# Set the entrypoint to serve index.html
# nginx will automatically serve index.html when you access the root
ENTRYPOINT ["nginx", "-g", "daemon off;"]
