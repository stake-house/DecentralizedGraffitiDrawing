package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/go-co-op/gocron"
	"github.com/namsral/flag"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
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
	X     uint   `json:"x"`
	Y     uint   `json:"y"`
	Color string `json:"color"`
}

type ValidatorLookup struct {
	Status string
	Data   []ValidatorLookupData
}
type ValidatorLookupData struct {
	PublicKey      string `json:"publickey"`
	ValidSignature bool   `json:"valid_signature"`
	ValidatorIndex uint   `json:"validatorindex"`
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
	MetricsEnabled  bool
	MetricsAddress  string
	MyValidators    string

	// Internal vars
	wallCache    *GraffitiWall
	inputCache   *DrawerData
	todoPixels   *DrawerData
	dataChanged  bool
	myValidators []uint

	// Prometheus stats
	promRPLTotalPixels = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "gww_pixels_total",
			Help: "Total number of pixels to be drawn (including already drawn), split by type",
		},
		[]string{"type"})
	promRPLTODOPixels = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "gww_pixels_todo",
			Help: "Number of pixels still to be drawn, split by type",
		},
		[]string{"type"})
	promRPLDrawSpeed = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "gww_pixels_speed",
			Help: "Number of pixels drawn in the last 24 hours",
		},
		[]string{"section"})
	promRPLMyPixels = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "gww_pixels_mine",
			Help: "Number of pixels drawn by my validators (as supplied)",
		},
		[]string{"validator"})
	promFetchLatency = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "gww_http_request_duration_seconds",
			Help:    "HTTP request latency in seconds.",
			Buckets: prometheus.LinearBuckets(0.01, 0.05, 10),
		},
		[]string{"url", "status"},
	)
)

func getJson(url string, target interface{}) error {
	var status string
	var timer *prometheus.Timer

	log.Printf("Fetching %s for json result....\n", url)
	client := &http.Client{Timeout: 10 * time.Second}

	if MetricsEnabled {
		timer = prometheus.NewTimer(prometheus.ObserverFunc(func(v float64) {
			promFetchLatency.WithLabelValues(url, status).Observe(v)
		}))
	}

	r, err := client.Get(url)
	if err != nil {
		return err
	}

	if MetricsEnabled {
		status = fmt.Sprintf("%d", r.StatusCode)
		timer.ObserveDuration()
	}

	defer r.Body.Close()
	if r.StatusCode < 200 || r.StatusCode > 299 {
		log.Printf("WARNING: Fetch of %s returned unexpected code: %d (%s) - retrying later...\n", url, r.StatusCode, http.StatusText(r.StatusCode))
		return nil
	}
	return json.NewDecoder(r.Body).Decode(target)
}

func fetchGraffitiWall() bool {
	newWallCache := &GraffitiWall{}

	err := getJson(BeaconURL, newWallCache)
	if err != nil {
		log.Printf("WARNING: Error fetching beaconcha.in graffitiwall: %s\n", err)
		return false
	}
	if newWallCache.Status != "OK" {
		log.Printf("WARNING: Unpexpected beaconcha.in graffitiwall status: %s\n", newWallCache.Status)
		return false
	} else {
		log.Printf("Graffitiwall fetched from beaconcha.in, status: %s\n", newWallCache.Status)
		wallCache = newWallCache
	}
	return true
}

func guessCurrentSlot() uint {
	// We have no proper way of obtaining this, so we'll calculate it. It's good enough for 24 hour estimates.
	genesis := time.Date(2020, 12, 1, 12, 0, 0, 0, time.UTC)
	secondsSinceGenesis := time.Since(genesis).Seconds()
	return uint(math.Round(secondsSinceGenesis / 12))
}

func init() {
	fmt.Printf("\n   +--------------------------+\n  /** Graffiti Wall Drawer **/\n +--------------------------+\n\nMade with passion by BenV and RamiRond.\n\n")

	flag.StringVar(&OutputFile, "output_file", "/graffiti/graffiti.txt", "File to write graffiti output to. Will be overwritten!")
	flag.StringVar(&InputURL, "input_url", "/graffiti/imagedata.json", "URL or path to file to source pixeldata from")
	flag.StringVar(&ConsensusClient, "consensus_client", "", "teku, nimbus, lighthouse, prysm")
	flag.StringVar(&NimbusURL, "nimbus_url", "", "URL to Nimbus (if that's your selected client), e.g. http://127.0.0.1:5052")
	flag.StringVar(&GraffitiPrefix, "graffiti_prefix", "", "Optional graffiti prefix, e.g. 'RPL-L v1.2.3'.")
	flag.StringVar(&Network, "network", "mainnet", "Network to draw own, e.g. mainnet, gnosis, prater")
	flag.StringVar(&MyValidators, "my_validators", "", "Comma separated string of validator indices AND/OR eth1 depositor addresses [e.g. node address]\n\t\t(checked against https://beaconcha.in/api/v1/docs/index.html#/Validator/get_api_v1_validator_eth1__eth1address_) that use the output of this drawer.\n\t\tE.g., 123,321 or 0x0123456789abcdefedcba9876543210123456789. Used only for metrics!")
	flag.IntVar(&UpdateWallTime, "update_wall_time", 600, "Time between beaconcha.in updates")
	flag.IntVar(&UpdateInputTime, "update_input_time", 600, "Time between input updates - only if remote URL is used. File will be instantly reloaded when changed.")
	flag.IntVar(&UpdatePixelTime, "update_pixel_time", 60, "Time between output updates")
	flag.BoolVar(&MetricsEnabled, "metrics_enabled", true, "Enable metrics server")
	flag.StringVar(&MetricsAddress, "metrics_address", ":9106", " Metrics listen [address]:port")
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
	if len(OutputFile) == 0 {
		log.Fatalf("Fatal: empty output filename provided, please specify where you want the output to be written to!")
	}
	fi, err := os.Stat(OutputFile)
	if err == nil && fi.IsDir() {
		log.Fatalf("Fatal: output file [%s] is a directory! Please change/remove it and try again.\n", OutputFile)
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

	// Parse my Validators
	myValidators = make([]uint, 0, 10)
	eth1re := regexp.MustCompile(`^0x[a-fA-F0-9]{40}$`)
	if len(MyValidators) > 0 {
		for _, val := range strings.Split(MyValidators, ",") {
			// See if this is an eth1 address, if so query beaconchain.
			if strings.HasPrefix(val, "0x") {
				if !eth1re.MatchString(val) {
					log.Fatalf("ERROR: Supplied validator pubkey input %s is not something we can handle at the moment, expecting 0x<40 hex chars>, e.g. 0xD33526068D116cE69F19A9ee46F0bd304F21A51f\n", val)
				}
				validators := &ValidatorLookup{}
				lookupURL := fmt.Sprintf("https://beaconcha.in/api/v1/validator/eth1/%s", val)
				log.Printf("My Validator supplied pubkey %s, looking up...", val)
				err := getJson(lookupURL, &validators)
				if err != nil {
					log.Fatalf("ERROR: Validator lookup with key %s failed: %s\n", val, err)
				}
				if len(validators.Data) == 0 {
					log.Printf("WARNING: Validator lookup results for pubkey %s had 0 entries. Typo? Wrong address? Make sure this is the address that made the deposits, e.g. rocket pool node address.\n", val)
				}
				for _, v := range validators.Data {
					myValidators = append(myValidators, v.ValidatorIndex)
				}
			} else {
				// Nope
				i, err := strconv.Atoi(val)
				if err != nil {
					log.Fatalf("Error parsing validator index %s, make sure you give the index and not the pubkey to my_validators! %s\n", val, err)
				}
				myValidators = append(myValidators, uint(i))
			}
		}
		log.Printf("Registered %d validators for 'pixels drawn by me'-metrics: %+v", len(myValidators), myValidators)
	} else {
		log.Printf("NOTE: No validators supplied as mine, thus pixels_mine metric will be absent!\n")
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

	// Let's try to write an initial graffiti file so we don't block any VC that won't start without one.
	if _, err := os.Stat(OutputFile); os.IsNotExist(err) {
		graffiti := ""
		if len(GraffitiPrefix) > 0 {
			graffiti = strings.TrimSpace(fmt.Sprintf("%.16s %s", GraffitiPrefix, graffiti))
		}
		if writeGraffiti(graffiti) {
			log.Printf("Absent graffiti file -> wrote template to [%s] to prevent blocking VC from starting...\n", OutputFile)
		} else {
			log.Printf("WARNING: Could not write graffiti-file [%s] -- your VC might refuse to start without it!", OutputFile)
		}
	}
}

func isMyValidator(index uint) bool {
	for _, i := range myValidators {
		if i == index {
			return true
		}
	}
	return false
}

func updateInput() bool {
	newData := &DrawerData{}
	if InputIsURL {
		err := getJson(InputURL, &newData.Data)
		if err != nil {
			log.Printf("ERROR: Could not parse input data from supplied URL [%s]: %s\n", InputURL, err)
			return false
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

func updateGraffiti() bool {
	log.Printf("Updating graffiti...\n")

	// Recalculate todo pixels if anything changed
	if dataChanged || todoPixels == nil {
		// make sure we have a graffiti wall already, otherwise we'll wait till next run
		if wallCache == nil {
			log.Printf("Wall not available yet, waiting...\n")
			return false
		}
		if inputCache == nil {
			log.Printf("Input data not available yet, waiting...\n")
			return false
		}

		dataChanged = false
		todoPixels = &DrawerData{}

		// Make a lookup dict for walldata
		curSlot := guessCurrentSlot()
		pixelsPerDayGlobal := 0
		wallCheck := make(map[string]*GraffitiWallPixel)
		for _, p := range wallCache.Data {
			pixel := p // get a unique pointer, thanks go
			wallCheck[fmt.Sprintf("%03d:%03d", pixel.X, pixel.Y)] = &pixel
			if pixel.Slot >= (curSlot - 7200) {
				pixelsPerDayGlobal++
			}
		}

		completed := 0
		skipped := 0
		wrong := 0
		pixelsPerDayRPL := 0
		totalWhite := 0
		todoWhite := 0
		myPixels := make(map[string]uint) // val idx -> pixels
		pcre := regexp.MustCompile(`^[a-f0-9]{6}$`)
		for _, pixel := range inputCache.Data {
			// Is this pixel sane?
			pixel.Color = strings.TrimSpace(strings.ToLower(pixel.Color))
			if pixel.X > 999 || pixel.Y > 999 || !pcre.MatchString(pixel.Color) {
				log.Printf("WARNING: Input json has invalid pixel: %d,%d %s - skipping!\n", pixel.X, pixel.Y, pixel.Color)
				continue
			}
			// Is it already drawn?
			checkIdx := fmt.Sprintf("%03d:%03d", pixel.X, pixel.Y)
			// White pixels can be skipped, so empty entries are OK for them
			if pixel.Color == "ffffff" {
				totalWhite++
			}
			if wallCheck[checkIdx] == nil && pixel.Color == "ffffff" {
				// White pixel, no need to draw
				todoWhite++
				skipped++
			} else if wallCheck[checkIdx] != nil && strings.ToLower(wallCheck[checkIdx].Color) == pixel.Color {
				completed++
				// Speed Stats
				if wallCheck[checkIdx].Slot >= (curSlot - 7200) {
					pixelsPerDayRPL++
				} else {
					// log.Printf("Pixel %s was drawn %07d slots ago [curslot %d vs %07d of this pixel]\n", checkIdx, curSlot - wallCheck[checkIdx].Slot, curSlot, wallCheck[checkIdx].Slot)
				}
				// Did we draw this?
				if isMyValidator(wallCheck[checkIdx].Validator) {
					vIdx := fmt.Sprintf("%d", wallCheck[checkIdx].Validator)
					if _, ok := myPixels[vIdx]; !ok {
						myPixels[vIdx] = 0
					}
					myPixels[vIdx]++
				}
			} else {
				if wallCheck[checkIdx] != nil && strings.ToLower(wallCheck[checkIdx].Color) != pixel.Color {
					wrong++
				}
				todoPixels.Data = append(todoPixels.Data, pixel)
			}
		}
		if MetricsEnabled {
			promRPLTotalPixels.WithLabelValues("Normal").Set(float64(len(inputCache.Data) - totalWhite))
			promRPLTotalPixels.WithLabelValues("White").Set(float64(totalWhite))
			promRPLTODOPixels.WithLabelValues("Normal").Set(float64(len(todoPixels.Data) - wrong))
			promRPLTODOPixels.WithLabelValues("White").Set(float64(todoWhite))
			promRPLTODOPixels.WithLabelValues("Fix").Set(float64(wrong))
			promRPLDrawSpeed.WithLabelValues("RPL").Set(float64(pixelsPerDayRPL))
			promRPLDrawSpeed.WithLabelValues("Global").Set(float64(pixelsPerDayGlobal))
			for vIdx, val := range myPixels {
				promRPLMyPixels.WithLabelValues(vIdx).Set(float64(val))
			}
		}
		log.Printf("STATUS: TODO %d pixel(s) [%d wrong to fix], %d already painted, %d skipped/ignored since they're white!\n", len(todoPixels.Data), wrong, completed, skipped)
	}

	// grab pixel, generate graffiti, output
	if todoPixels == nil {
		log.Printf("No todoPixels data available yet. Retry soon...\n")
		return false
	}
	if len(todoPixels.Data) == 0 {
		log.Printf("Zero todoPixels available... no graffiti for now.... [guard mode]\n")
		return false
	}
	index := rand.Intn(len(todoPixels.Data))
	pixel := todoPixels.Data[index]
	log.Printf(" * Randomly selected todo pixel: [%d,%d] #%s\n", pixel.X, pixel.Y, pixel.Color)

	// Format graffiti and send it out
	graffiti := getGraffiti(pixel)
	if len(GraffitiPrefix) > 0 {
		// pixel is 15, so we've 17 left
		graffiti = strings.TrimSpace(fmt.Sprintf("%.16s %s", GraffitiPrefix, graffiti))
	}
	return writeGraffiti(graffiti)
}

func getGraffitiTemplate() string {
	// Returns a consensus-client specific template that works for Sprintf
	template := "%s"
	switch ConsensusClient {
	case "lighthouse":
		template = `default: %s`
	case "prysm":
		template = `ordered:` + "\n" + `  - "%s"`
	}
	return template
}

func writeGraffiti(graffiti string) bool {
	graffiti = fmt.Sprintf(getGraffitiTemplate(), graffiti)
	if ConsensusClient == "nimbus" {
		err := setNimbusGraffiti(graffiti)
		if err != nil {
			log.Printf(" ❌ WARNING: Could not set Nimbus graffiti to [%s]: %s\n", graffiti, err)
			return false
		}
	} else {
		tmp := []byte(fmt.Sprintf("%s\n", graffiti))
		err := os.WriteFile(OutputFile, tmp, 0644)
		if err != nil {
			log.Printf(" ❌ WARNING: Could not write graffiti %s to [%s]: %s\n", graffiti, OutputFile, err)
			return false
		}
	}
	log.Printf(" ✅ graffiti update OK [%s].\n", graffiti)
	return true
}

func getGraffiti(pixel DrawerPixel) string {
	return fmt.Sprintf("gw:%03d%03d%s", pixel.X, pixel.Y, pixel.Color)
}

func setNimbusGraffiti(graffiti string) error {
	// We send the graffiti data directly to nimbus' api at NIMBUSURL/nimbus/v1/graffiti
	url := fmt.Sprintf("%s%s", strings.TrimSuffix(NimbusURL, "/"), "/nimbus/v1/graffiti")
	log.Printf("Sending graffiti [%s] to nimbus at %s...\n", graffiti, url)

	// response = requests.post(url, headers=header, data=graffiti)
	client := &http.Client{Timeout: 10 * time.Second}
	r, err := client.Post(url, "text/plain", bytes.NewBufferString(graffiti))
	if err != nil {
		return err
	}
	defer r.Body.Close()
	reply, _ := io.ReadAll(r.Body)
	if r.StatusCode > 199 && r.StatusCode < 399 {
		log.Printf("Server at %s accepted our graffiti, response code: %d, response body of %d bytes\n", url, r.StatusCode, len(reply))
	} else {
		log.Printf("Server at %s did NOT accept our graffiti! Response code: %d, response body of %d bytes\n", url, r.StatusCode, len(reply))
		if len(reply) > 0 {
			log.Printf("Response (first 2048 chars):\n=====\n%.2048s\n=====\n", reply)
		}
		return fmt.Errorf("Invalid response from Nimbus API call, code %d", r.StatusCode)
	}
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
			log.Printf("WARNING: Failed to create input watcher for file, reverting to cron updates: %s", err)
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

	// Enable metrics if requested
	h := &http.Server{Addr: MetricsAddress}
	if MetricsEnabled {
		go func() {
			http.Handle("/metrics", promhttp.Handler())
			log.Printf("Trying to start Metrics Server at http://%s/metrics\n", MetricsAddress)
			if err := h.ListenAndServe(); err != nil {
				log.Printf("Error trying to start Metrics server http://%s/metrics (will continue without)! %s\n", MetricsAddress, err)
			}
		}()
	}

	<-done
}
