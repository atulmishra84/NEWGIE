FROM nginx:1.27-alpine
COPY index.html dashboard.html /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
COPY demo/ /usr/share/nginx/html/demo/
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
