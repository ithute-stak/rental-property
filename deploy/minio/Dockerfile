FROM golang:1.24.8-alpine AS build

ARG MINIO_VERSION=RELEASE.2025-10-15T17-29-55Z
ENV CGO_ENABLED=0

RUN apk add --no-cache ca-certificates git
RUN go install -v "github.com/minio/minio@${MINIO_VERSION}"

FROM alpine:3.22

RUN apk add --no-cache ca-certificates tzdata
COPY --from=build /go/bin/minio /usr/local/bin/minio

EXPOSE 9000 9001
ENTRYPOINT ["minio"]
