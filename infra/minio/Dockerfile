FROM golang:1.25-bookworm AS server-build
ENV CGO_ENABLED=0 GOBIN=/out GOMAXPROCS=2 GOMEMLIMIT=512MiB GOFLAGS=-p=2
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build go install github.com/minio/minio@9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a

FROM golang:1.25-bookworm AS client-build
ENV CGO_ENABLED=0 GOBIN=/out GOMAXPROCS=2 GOMEMLIMIT=512MiB GOFLAGS=-p=2
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build go install github.com/minio/mc@77f82e18b5401a65958f1619df6ebb994634bd88

FROM debian:bookworm-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*

FROM runtime AS server
COPY --from=server-build /out/minio /usr/local/bin/minio
ENTRYPOINT ["minio"]

FROM runtime AS client
COPY --from=client-build /out/mc /usr/local/bin/mc
ENTRYPOINT ["mc"]
