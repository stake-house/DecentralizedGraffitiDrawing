FROM golang:1.19-alpine AS builder

RUN apk update && apk add --no-cache git ca-certificates && update-ca-certificates

ENV USER=rpl
ENV UID=10000

RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    "${USER}"

WORKDIR $GOPATH/src/drawer/
COPY . .

ENV CGO_ENABLED=0
RUN go mod download
RUN go build -ldflags="-w -s" -o /go/bin/drawer

FROM scratch

# Import from builder.
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group
COPY --from=builder /go/bin/drawer /go/bin/drawer

USER rpl:rpl

ENTRYPOINT ["/go/bin/drawer"]
