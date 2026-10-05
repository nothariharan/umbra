FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
COPY vendor ./vendor
COPY *.go ./
COPY web ./web
RUN CGO_ENABLED=0 go build -mod=vendor -trimpath -ldflags="-s -w" -o /pocketful .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /pocketful /pocketful
ENV PORT=8080
EXPOSE 8080
USER nobody
ENTRYPOINT ["/pocketful"]
