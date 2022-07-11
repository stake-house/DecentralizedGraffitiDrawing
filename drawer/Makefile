drawer: drawer.go
	go mod download
	go build -ldflags="-s -w" -o drawer drawer.go

docker:
	docker build -f Dockerfile -t graffiti-drawer:latest .
