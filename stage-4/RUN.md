# Pocketful Stage 4

Build and run (from this directory):

```sh
docker build -t pocketful-stage4 . && docker run --rm -e PORT=8080 -p 8080:8080 pocketful-stage4
```

Health check: `GET http://localhost:8080/health`
