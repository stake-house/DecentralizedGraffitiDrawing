drawer: drawer.go
	go mod download
	go build -ldflags="-s -w" -o drawer drawer.go

docker:
	docker build -f Dockerfile -t graffiti-drawer:latest .

modtidy:
	docker run --rm -v $(PWD):/go/src golang:1.19-alpine sh -c "cd /go/src ; go mod tidy -v"


