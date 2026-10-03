# Pocketful Stage 1

Build and run (from this directory):

```sh
docker build -t pocketful-stage1 . && docker run --rm -e PORT=8080 -p 8080:8080 pocketful-stage1
```

Health check: `GET http://localhost:8080/health`
