package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/fsnotify/fsnotify"
	"github.com/go-co-op/gocron"
	"github.com/namsral/flag"
	"io"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"regexp"
	"strings"
	"syscall"
	"time"
)

type GraffitiWallPixel struct {
	Color     string
	Slot      uint
	Validator uint
	X         uint
	Y         uint
}

type GraffitiWall struct {
	Status string
	Data   []GraffitiWallPixel
}

type DrawerPixel struct {
	X     uint   `json: x`
	Y     uint   `json: y`
	Color string `json: color`
}

type DrawerData struct {
	Data []DrawerPixel
}

var (
	OutputFile      string
	InputURL        string
	InputIsURL      bool
	ConsensusClient string
	NimbusURL       string
	Network         string
	UpdateWallTime  int
	UpdateInputTime int
	UpdatePixelTime int
	BeaconURL       string
	GraffitiPrefix  string
	wallCache       *GraffitiWall
	inputCache      *DrawerData
	todoPixels      *DrawerData
	dataChanged     bool
)

func getJson(url string, target interface{}) error {
	log.Printf("Fetching %s for json result....\n", url)
	client := &http.Client{Timeout: 10 * time.Second}
	r, err := client.Get(url)
	if err != nil {
		return err
	}
	defer r.Body.Close()
	return json.NewDecoder(r.Body).Decode(target)
}

func fetchGraffitiWall() bool {
	wallCache = &GraffitiWall{}

	err := getJson(BeaconURL, wallCache)
	if err != nil {
		log.Fatalln(err)
	}
	if wallCache.Status != "OK" {
		log.Printf("WARNING: Unpexpected beaconcha.in graffitiwall status: %s\n", wallCache.Status)
	} else {
		log.Printf("Graffitiwall fetched from beaconcha.in, status: %s\n", wallCache.Status)
	}

	return true
}

func init() {
	flag.StringVar(&OutputFile, "output_file", "/graffiti/graffiti.txt", "File to write graffiti to")
	flag.StringVar(&InputURL, "input_url", "/graffiti/imagedata.json", "URL or path to file to source pixeldata from")
	flag.StringVar(&ConsensusClient, "consensus_client", "", "teku, nimbus, lighthouse, prysm")
	flag.StringVar(&NimbusURL, "nimbus_url", "", "URL to Nimbus (if that's your selected client), e.g. http://127.0.0.1:5052")
	flag.StringVar(&GraffitiPrefix, "graffiti_prefix", "", "Optional graffiti prefix, e.g. 'RPL-L v1.2.3'. Not for Gnosis network (yet).")
	flag.StringVar(&Network, "network", "mainnet", "Network to draw own, e.g. mainnet, gnosis, prater")
	flag.IntVar(&UpdateWallTime, "update_wall_time", 600, "Time between beaconcha.in updates")
	flag.IntVar(&UpdateInputTime, "update_input_time", 600, "Time between input updates - only if remote URL is used. File will be instantly reloaded when changed.")
	flag.IntVar(&UpdatePixelTime, "update_pixel_time", 60, "Time between output updates")
	flag.Parse()

	rand.Seed(time.Now().UnixNano())

	// Sanity
	ccre := regexp.MustCompile(`^(teku|nimbus|lighthouse|prysm)$`)
	ConsensusClient = strings.TrimSpace(strings.ToLower(ConsensusClient))
	if len(ConsensusClient) == 0 || !ccre.MatchString(ConsensusClient) {
		log.Fatalf("Error: invalid/no consensus client supplied, accepted values are: teku nimbus lighthouse prysm")
		return
	}
	if len(GraffitiPrefix) > 16 {
		log.Printf("WARNING: graffiti prefix is too long, will be truncated to [%.16s]!", GraffitiPrefix)
	}
	if Network == "gnosis" && len(GraffitiPrefix) > 0 {
		log.Printf("WARNING: graffiti prefix is disabled for Gnosis right now!")
	}
	if UpdatePixelTime <= 0 {
		UpdatePixelTime = 60
	}
	if UpdateWallTime <= 0 {
		UpdateWallTime = 600
	}
	if UpdateInputTime <= 0 {
		UpdateInputTime = 600
	}

	// Nimbus?
	if ConsensusClient == "nimbus" {
		if len(NimbusURL) == 0 {
			log.Fatalf("Error: nimbus selected, but no nimbus URL supplied.")
			return
		}
	}

	switch Network {
	case "mainnet":
		BeaconURL = "https://beaconcha.in/api/v1/graffitiwall"
	case "gnosis":
		BeaconURL = "https://beacon.gnosischain.com/api/v1/graffitiwall"
	default:
		BeaconURL = fmt.Sprintf("https://%s.beaconcha.in/api/v1/graffitiwall", Network)
	}

	// Input remote or file?
	re := regexp.MustCompile(`^https?://`)
	if re.MatchString(InputURL) {
		InputIsURL = true
		updateInput()
	} else {
		// Make sure input exists and can be loaded
		if fi, err := os.Stat(InputURL); err != nil {
			log.Fatalf("Input file %s does not exist! %s\n", InputURL, err)
		} else {
			log.Printf("Input file %s of size %d found.\n", InputURL, fi.Size())
		}
		if !updateInput() {
			log.Fatalf("Input file %s is not working for us :/\n", InputURL)
		}
	}
}

func updateInput() bool {
	newData := &DrawerData{}
	if InputIsURL {
		err := getJson(InputURL, &newData.Data)
		if err != nil {
			log.Fatalf("ERROR: Could not parse input data from supplied URL [%s]: %s\n", InputURL, err)
		}
	} else {
		inputFile, err := os.Open(InputURL)
		if err != nil {
			log.Fatalf("ERROR: Could not read input for graffiti: %s\nPlease supply either a valid path to input JSON file, OR a valid URL, e.g. https://.\n", err)
		}
		defer inputFile.Close()
		data, err := io.ReadAll(inputFile)
		if err != nil {
			log.Fatalf("ERROR: Could not read input for graffiti: %s\nPlease supply either a valid path to input JSON file, OR a valid URL, e.g. https://.\n", err)
		}
		err = json.Unmarshal(data, &newData.Data)
		if err != nil {
			log.Fatalf("ERROR: Could not parse input for graffiti: %s\nPlease supply either a valid path to input JSON file, OR a valid URL, e.g. https://.\n", err)
		}
	}
	log.Printf("Input now holds %d pixels\n", len(newData.Data))
	inputCache = newData
	dataChanged = true
	return true
}

func updateGraffiti() {
	log.Printf("Updating graffiti...\n")

	// Recalculate todo pixels if anything changed
	if dataChanged || todoPixels == nil {
		// make sure we have a graffiti wall already, otherwise we'll wait till next run
		if wallCache == nil {
			log.Printf("Wall not available yet, waiting...\n")
			return
		}
		if inputCache == nil {
			log.Printf("Input data not available yet, waiting...\n")
			return
		}

		dataChanged = false
		todoPixels = &DrawerData{}

		// Make a lookup dict for walldata
		wallCheck := make(map[string]string)
		for _, pixel := range wallCache.Data {
			// TODO: sanity check on beacon wall data, for now we'll just accept it since we're only comparing against it
			wallCheck[fmt.Sprintf("%s:%s", pixel.X, pixel.Y)] = strings.ToLower(pixel.Color)
		}

		completed := 0
		pcre := regexp.MustCompile(`^[a-f0-9]{6}$`)
		for _, pixel := range inputCache.Data {
			// Is this pixel sane?
			pixel.Color = strings.TrimSpace(strings.ToLower(pixel.Color))
			if pixel.X > 999 || pixel.Y > 999 || !pcre.MatchString(pixel.Color) {
				log.Printf("WARNING: Input json has invalid pixel: %d,%d %s - skipping!\n", pixel.X, pixel.Y, pixel.Color)
				continue
			}
			// Is it already drawn?
			if wallCheck[fmt.Sprintf("%s:%s", pixel.X, pixel.Y)] == strings.ToLower(pixel.Color) {
				completed++
			} else {
				todoPixels.Data = append(todoPixels.Data, pixel)
			}
		}
		log.Printf("STATUS: TODO %d pixel(s), %d already painted!\n", len(todoPixels.Data), completed)
	}

	// grab pixel, generate graffiti, output
	if todoPixels == nil {
		log.Printf("No todoPixels data available yet. Retry soon...\n")
		return
	}
	if len(todoPixels.Data) == 0 {
		log.Printf("Zero todoPixels available... no graffiti for now.... [guard mode]\n")
		return
	}
	index := rand.Intn(len(todoPixels.Data))
	pixel := todoPixels.Data[index]
	log.Printf(" * Randomly selected todo pixel: [%d,%d] #%s\n", pixel.X, pixel.Y, pixel.Color)

	// Format graffiti and send it out
	pre := ""
	post := ""
	switch ConsensusClient {
	case "lighthouse":
		pre = `default: `
	case "prysm":
		pre = `ordered:\n  - "`
		post = `"`
	}

	graffiti := getGraffiti(pixel, Network != "gnosis")

	if Network != "gnosis" && len(GraffitiPrefix) > 0 {
		// pixel is 15, so we've 17 left
		graffiti = strings.TrimSpace(fmt.Sprintf("%.16s %s", GraffitiPrefix, graffiti))
	}
	graffiti = fmt.Sprintf("%s%s%s", pre, graffiti, post)

	if ConsensusClient == "nimbus" {
		err := setNimbusGraffiti(graffiti)
		if err != nil {
			log.Printf(" ❌ WARNING: Could not set Nimbus graffiti to %s: %s\n", graffiti, err)
			return
		}
	} else {
		tmp := []byte(fmt.Sprintf("%s\n", graffiti))
		err := os.WriteFile(OutputFile, tmp, 0644)
		if err != nil {
			log.Printf(" ❌ WARNING: Could not write graffiti %s to %s: %s\n", graffiti, OutputFile, err)
			return
		}
	}
	log.Printf(" ✅ graffiti update OK.\n")
}

func getGraffiti(pixel DrawerPixel, newFormat bool) string {
	if newFormat {
		return fmt.Sprintf("gw:%03d%03d%s", pixel.X, pixel.Y, pixel.Color)
	} else {
		return fmt.Sprintf("graffitiwall:%d:%d:%s", pixel.X, pixel.Y, pixel.Color)
	}
}

func setNimbusGraffiti(graffiti string) error {
	// We send the graffiti data directly to nimbus' api at NIMBUSURL/api/nimbus/v1/graffiti
	url := fmt.Sprintf("%s%s", strings.TrimSuffix(NimbusURL, "/"), "/api/nimbus/v1/graffiti")
	log.Printf("Sending graffiti [%s] to nimbus at %s...\n", graffiti, url)

	// response = requests.post(url, headers=header, data=graffiti)
	client := &http.Client{Timeout: 10 * time.Second}
	r, err := client.Post(url, "text/plain", bytes.NewBufferString(graffiti))
	if err != nil {
		return err
	}
	defer r.Body.Close()
	reply, _ := io.ReadAll(r.Body)
	log.Printf("Server at %s accepted our graffiti, response code: %d, response body of %d bytes\n", url, r.StatusCode, len(reply))
	return nil
}

func writeWatcher(watcher *fsnotify.Watcher) {
	log.Printf("File watcher starting....")
	isChanged, isRemoved := false, false
	for {
		select {
		case event, ok := <-watcher.Events:
			if !ok {
				log.Printf("Watcher not ok??? %s\n", event)
				return
			}
			// log.Printf("Watcher event: %s\n", event)
			if event.Op&fsnotify.Remove == fsnotify.Remove {
				isChanged, isRemoved = true, true
			}
			if event.Op&fsnotify.Write == fsnotify.Write {
				log.Printf("Input file %s modified (%s)!\n", InputURL, event.Name)
				isChanged = true
			}
		case err, ok := <-watcher.Errors:
			if !ok {
				log.Printf("Watcher not ok??? %s\n", err)
				return
			}
			log.Printf("Watcher error: %s\n", err)
		}
		if _, err := os.Stat(InputURL); !os.IsNotExist(err) && (isRemoved || isChanged) {
			if isRemoved {
				log.Printf("Rewatching InputFile %s\n", InputURL)
				err := watcher.Add(InputURL)
				if err != nil {
					log.Printf("ERROR adding InputFile %s to watcher: %s", InputURL, err)
				}
				isChanged, isRemoved = true, false
			}
			if isChanged {
				updateInput()
				isChanged = false
			}
		}
	}
}

func main() {
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	done := make(chan bool, 1)

	log.Printf(" * Drawer starting for %s, generating output every %d seconds.\n", ConsensusClient, UpdatePixelTime)
	cron := gocron.NewScheduler(time.UTC)

	// Cronjob to pull input URL every UpdateInputTime, OR set a file watcher
	if InputIsURL {
		cron.Every(UpdateInputTime).Seconds().Do(updateInput)
	} else {
		// Set watcher
		watcher, err := fsnotify.NewWatcher()
		if err != nil {
			log.Printf("WARNING: Failed to create input watcher for file, reverting to cron updates: ", err)
			cron.Every(UpdateInputTime).Seconds().Do(updateInput)
		} else {
			go writeWatcher(watcher)
			err = watcher.Add(InputURL)
			if err != nil {
				log.Fatalf("ERROR adding InputFile %s to watcher: %s", InputURL, err)
			}
		}
		defer watcher.Close()
		log.Printf("File Watcher on %s installed.\n", InputURL)
	}

	cron.Every(UpdateWallTime).Seconds().Do(fetchGraffitiWall)
	// Slight delay so we hopefully have all data before generation
	cron.Every(UpdatePixelTime).Seconds().StartAt(time.Now().Add(time.Duration(5 * time.Second))).Do(updateGraffiti)

	go func() {
		sig := <-sigs
		log.Printf("%s signal caught, bye bye!\n", sig)
		done <- true
	}()

	cron.StartAsync()
	<-done
}
