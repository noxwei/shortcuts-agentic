# Cherri iOS Shortcut Programming Guide

Comprehensive reference for building iOS Shortcuts programmatically using the Cherri compiler. Based on hard-learned lessons from the shortcuts-agentic project.

---

## 1. Overview

### What is Cherri?

Cherri is a programming language that compiles to iOS/macOS `.shortcut` files (the binary format Apple Shortcuts uses). It replaces the drag-and-drop Shortcuts editor with a text-based workflow.

- **Compiler location:** `~/go/bin/cherri`
- **Source:** [github.com/nicknicknicknick/cherri](https://github.com/nicknicknicknick/cherri)
- **File extension:** `.cherri` (source) -> `.shortcut` (compiled binary)

### Compilation + Signing Pipeline

```
.cherri source
    |
    v
~/go/bin/cherri filename.cherri
    |
    v
.shortcut binary (signed by default)
    |
    v
Open in Shortcuts app -> import
```

Cherri signs shortcuts by default using a local signing mechanism. The signed `.shortcut` file can be opened directly on macOS or transferred to iOS for import.

### Import to iOS/macOS

1. **macOS:** Double-click the `.shortcut` file, or use `open filename.shortcut`
2. **iOS via AirDrop:** Send the `.shortcut` file from Mac to iPhone
3. **iOS via file share:** Place in iCloud Drive, open from Files app
4. **Programmatic:** Use `cherri --open` to auto-open after compilation

---

## 2. Critical Bugs & Workarounds

These are hard-learned lessons from real-world testing. Each one cost hours of debugging.

### Variable interpolation in URL/header strings crashes Shortcuts import UI

When you use `{variable}` interpolation inside URL strings or HTTP header values across **multiple web actions in the same shortcut**, the Shortcuts app crashes during import with a `WFAppKitAutocompleteTextView` layout error.

**Bad -- crashes on import:**
```
const url = "https://example.com"
const key = "my-api-key"
const data = downloadURL("{url}/endpoint1", {"X-Key": "{key}"})
const more = jsonRequest("{url}/endpoint2", "POST", {}, {"X-Key": "{key}"})
```

**Good -- hardcode URLs and headers inline:**
```
const data = downloadURL("https://example.com/endpoint1", {"X-Key": "my-api-key"})
const more = jsonRequest("https://example.com/endpoint2", "POST", {}, {"X-Key": "my-api-key"})
```

Variable interpolation in prompts, `show()`, and `speak()` is fine. The crash only affects URL and header string parameters in web actions.

Evidence: `test-combo.cherri` (uses variables in URLs, crashes) vs `test-combo2.cherri` (hardcoded URLs, works). The working shortcuts (`whats-next-book.cherri`, `library-digest.cherri`, `surprise-me-book.cherri`) all hardcode their URLs and headers.

### Opening multiple .shortcut files at once crashes Shortcuts

If you batch-open `.shortcut` files (e.g., `open *.shortcut`), Shortcuts will crash. Import them one at a time with a delay between each.

### Long inline text strings trigger layout crash

Very long text strings in Cherri source (especially multi-line prompt strings) can cause a `WFAppKitAutocompleteTextView` layout crash when the shortcut is opened in the Shortcuts editor. Keep prompts concise and under ~500 characters per string. If you need longer text, break it across multiple variables.

### Shortcuts crash-loops on start

If the Shortcuts app won't open or immediately crashes:

```bash
rm -rf ~/Library/Saved\ Application\ State/com.apple.shortcuts.savedState
```

This clears the saved state that tries to re-open the last shortcut that crashed it.

### Never use cherri -o flag

Known bug: the `-o` flag can overwrite directories with a binary file, destroying entire project trees. Always compile by `cd`-ing into the target directory and running `cherri filename.cherri` with a relative path.

### Always cd into the target directory

Never pass directory paths as arguments to cherri. The compiler writes output to the same directory as the input file.

```bash
# CORRECT
cd /path/to/shortcuts/generated && ~/go/bin/cherri my-shortcut.cherri

# WRONG -- risk of directory overwrite
~/go/bin/cherri /path/to/shortcuts/generated/my-shortcut.cherri
```

### Default signing works better than --hubsign

For local compilation, the default signing mechanism is more reliable than `--hubsign` (RoutineHub remote signing). Use `--skip-sign` only when you know you will sign later or are testing compilation only.

### Cherri requires explicit #include for each action category

If you use an action from a category (e.g., `askChatGPT` from intelligence), you must `#include 'actions/intelligence'` at the top. The compiler error message tells you which include is missing. The `basic` category is auto-included.

---

## 3. Project Structure

### Directory Layout

```
shortcuts/
    *.cherri              # Hand-written shortcut source files (18 files)
    generated/            # AI-generated shortcuts (output directory)
        *.cherri          # Generated source files
        *.shortcut        # Compiled binary files
```

### Pipeline: .cherri -> .shortcut

1. **Write or generate** `.cherri` source code
2. **Compile:** `cd shortcuts/generated && ~/go/bin/cherri my-shortcut.cherri`
3. **Import:** Open the resulting `.shortcut` file in Shortcuts app
4. **Test:** Run the shortcut on device

For the agentic generator pipeline (automated):

```
User describes shortcut in natural language
    |
    v
POST /v1/shortcuts/generate
    |
    v
Claude Haiku generates .cherri source (with system prompt + few-shot examples)
    |
    v
cherri compiles .cherri -> .shortcut (with --skip-sign for server-side)
    |
    v
If compilation fails: error fed back to Haiku for self-repair (1 retry)
    |
    v
GET /v1/shortcuts/{id}/download serves the .shortcut file
```

### Signing Options

| Flag | Description | When to use |
|------|-------------|-------------|
| (default) | Local signing | Normal local compilation |
| `--hubsign` | RoutineHub remote signing | Sharing publicly on RoutineHub |
| `--signing-server=URL` | Custom signing server | Self-hosted signing service |
| `--skip-sign` | No signing | Server-side compilation, testing |
| `-s=anyone` | Allow anyone to import | Public distribution |
| `-s=contacts` | Contacts only (default) | Personal use |

---

## 4. Action Reference

### basic (auto-included)

No `#include` needed. These actions are always available.

#### Output & Display

| Action | Signature | Description |
|--------|-----------|-------------|
| `show` | `show(text input)` | Show result dialog |
| `alert` | `alert(text alert, text ?title)` | Alert with OK button |
| `confirm` | `confirm(text alert, text ?title)` | Alert with OK + Cancel (cancel stops shortcut) |
| `showNotification` | `showNotification(text body, text ?title, bool ?playSound=true, variable ?attachment)` | System notification |
| `output` | `output(text output)` | Stop and output (silent if nowhere to output) |
| `mustOutput` | `mustOutput(text output, text response)` | Stop and output with fallback |
| `outputOrClipboard` | `outputOrClipboard(text output)` | Output or copy to clipboard |
| `quicklook` | `quicklook(variable input)` | Quick Look preview |
| `contentGraph` | `contentGraph(variable input)` | Content graph display |

#### Input

| Action | Signature | Description |
|--------|-----------|-------------|
| `prompt` | `prompt(text prompt, inputType ?inputType="Text", text ?defaultValue, text ?multiline=true)` | Ask for input |

Input types: `Text`, `Number`, `URL`, `Date`, `Time`, `Date and Time`

#### Utility

| Action | Signature | Description |
|--------|-----------|-------------|
| `comment` | `comment(rawtext text)` | Add comment action |
| `count` | `count(variable input, countType ?type="Items"): number` | Count items/chars/words/sentences/lines |
| `nothing` | `nothing()` | Clear current output |
| `number` | `number(variable number): number` | Create number value |
| `typeOf` | `typeOf(variable input): text` | Get type of input |
| `stop` | `stop()` | Stop shortcut execution |
| `search` | `search(text query, number ?limit=5, array ?resultType)` | Spotlight/search |

#### Control Flow

| Action | Signature | Description |
|--------|-----------|-------------|
| `wait` | `wait(number seconds)` | Wait N seconds |
| `waitToReturn` | `waitToReturn()` | Wait for user to return to Shortcuts |

### intelligence

```
#include 'actions/intelligence'
```

#### Language Models

| Action | Signature | Description |
|--------|-----------|-------------|
| `askChatGPT` | `askChatGPT(text prompt, bool ?followUp=false, generativeResultType ?resultType="Automatic")` | Ask ChatGPT |
| `askDeviceLLM` | `askDeviceLLM(text prompt, bool ?followUp=false, generativeResultType ?resultType="Automatic")` | On-device Apple Intelligence LLM |
| `askCloudLLM` | `askCloudLLM(text prompt, bool ?followUp=false, generativeResultType ?resultType="Automatic")` | Private Cloud Compute LLM |
| `askLLM` | `askLLM(text prompt, LLMModel ?model="Private Cloud Compute", bool ?followUp=false, generativeResultType ?resultType="Automatic")` | Ask specific LLM |

LLM models: `Private Cloud Compute`, `Apple Intelligence on Device`, `ChatGPT`

Result types: `Text`, `Number`, `Date`, `Boolean`, `List`, `Dictionary`

#### Image Generation

| Action | Signature | Description |
|--------|-----------|-------------|
| `generateImage` | `generateImage(text prompt, variable ?image, imagePlaygroundStyle ?style="animation", saveToPlaygroundBehavior ?saveToPlayground="always")` | Image Playground |

Styles: `animation`, `illustration`, `sketch`, `chatgpt`, `chatgpt_oil_painting`, `chatgpt_watercolor`, `chatgpt_vector`, `chatgpt_anime`, `chatgpt_print`

#### Writing Tools

| Action | Signature | Description |
|--------|-----------|-------------|
| `adjustTextTone` | `adjustTextTone(text text, textTone tone): text` | Adjust tone (friendly/professional/concise) |
| `generateList` | `generateList(text text): text` | Convert text to list |
| `generateTable` | `generateTable(text text): text` | Convert text to table |
| `generateKeyPoints` | `generateKeyPoints(text text): text` | Extract key points |
| `generateSummary` | `generateSummary(text text): text` | Summarize text |
| `generateProofread` | `generateProofread(text text): text` | Proofread text |
| `generateRewrite` | `generateRewrite(text text): text` | Rewrite text |

### web

```
#include 'actions/web'
```

#### HTTP Requests

| Action | Signature | Description |
|--------|-----------|-------------|
| `downloadURL` | `downloadURL(text url, dictionary ?headers)` | GET request (download URL contents) |
| `jsonRequest` | `jsonRequest(text url, HTTPMethod ?method, dictionary ?body, dictionary ?headers)` | JSON request (POST/PUT/PATCH/DELETE) |
| `formRequest` | `formRequest(text url, HTTPMethod ?method, dictionary ?body, dictionary ?headers)` | Form-encoded request |
| `fileRequest` | `fileRequest(text url, HTTPMethod ?method, dictionary ?body, dictionary ?headers)` | File upload request |

HTTP methods: `POST`, `PUT`, `PATCH`, `DELETE`

#### Web Content

| Action | Signature | Description |
|--------|-----------|-------------|
| `getArticle` | `getArticle(text webpage)` | Get article from webpage |
| `getWebpageContents` | `getWebpageContents(text url)` | Get webpage contents |
| `getWebPageDetail` | `getWebPageDetail(variable webpage, webpageDetail detail)` | Get webpage detail |
| `openURL` | see basic URL handling | Open a URL |
| `showWebpage` | `showWebpage(text url, bool ?useReader)` | Show in Safari |
| `searchWeb` | `searchWeb(searchEngine engine, text query)` | Search the web |
| `getCurrentURL` | `getCurrentURL()` | Get current Safari URL |
| `runJavaScriptOnWebpage` | `runJavaScriptOnWebpage(text javascript)` | Run JS in Safari |

Search engines: `Amazon`, `Bing`, `DuckDuckGo`, `eBay`, `Google`, `Reddit`, `Twitter`, `Yahoo!`, `YouTube`

#### URLs

| Action | Signature | Description |
|--------|-----------|-------------|
| `expandURL` | `expandURL(text url)` | Expand shortened URL |
| `addToReadingList` | `addToReadingList(text ...url)` | Add to Safari Reading List |

#### RSS

| Action | Signature | Description |
|--------|-----------|-------------|
| `getRSS` | `getRSS(number items, text url)` | Get RSS feed |
| `getRSSFeeds` | `getRSSFeeds(text urls)` | Get multiple RSS feeds |

#### Giphy

| Action | Signature | Description |
|--------|-----------|-------------|
| `getGifs` | `getGifs(text query, number ?gifs=1)` | Get GIFs from Giphy |
| `searchGiphy` | `searchGiphy(text query)` | Search Giphy |

### scripting

```
#include 'actions/scripting'
```

#### Dictionaries

| Action | Signature | Description |
|--------|-----------|-------------|
| `getDictionary` | `getDictionary(variable input): dictionary` | Parse input as dictionary |
| `getValue` | `getValue(dictionary dictionary, text key)` | Get value by key (for constants) |
| `getKeys` | `getKeys(dictionary dictionary): array` | Get all keys |
| `getValues` | `getValues(dictionary dictionary): array` | Get all values |
| `setValue` | `setValue(variable dictionary, text key, text value)` | Set value in dictionary |

Note: For non-constant dictionaries, use `dictionary['key']` syntax instead of `getValue`.

#### Lists

| Action | Signature | Description |
|--------|-----------|-------------|
| `list` | `list(text ...listItem)` | Create a list |
| `chooseFromList` | `chooseFromList(variable list, text ?prompt, bool ?selectMultiple=false, bool ?selectAll=false)` | User picks from list |
| `getListItem` | `getListItem(variable list, number index)` | Get item at index (1-based) |
| `getListItems` | `getListItems(variable list, number start, number end): array` | Get range of items |
| `getFirstItem` | `getFirstItem(variable list)` | First item |
| `getLastItem` | `getLastItem(variable list)` | Last item |
| `getRandomItem` | `getRandomItem(variable list)` | Random item |

#### Apps

| Action | Signature | Description |
|--------|-----------|-------------|
| `openApp` | `openApp(text appID)` | Open an app |
| `killApp` | `killApp(text appID)` | Kill an app (no save prompt) |
| `quitApp` | `quitApp(text appID)` | Quit an app |
| `hideApp` | `hideApp(text appID)` | Hide an app |
| `splitApps` | `splitApps(text firstAppID, text secondAppID, appSplitRatio ?ratio="half")` | Split screen |

#### Numbers

| Action | Signature | Description |
|--------|-----------|-------------|
| `randomNumber` | `randomNumber(number min, number max): number` | Random number |
| `formatNumber` | `formatNumber(number number, number ?decimalPlaces=2): number` | Format number |
| `getNumbers` | `getNumbers(variable input): number` | Extract numbers from input |

#### Items

| Action | Signature | Description |
|--------|-----------|-------------|
| `getName` | `getName(variable item)` | Get item name |
| `setName` | `setName(variable item, text name, bool ?includeFileExtension=false)` | Set item name |

#### System

| Action | Signature | Description |
|--------|-----------|-------------|
| `dismissSiri` | `dismissSiri()` | Dismiss Siri |
| `searchPasswords` | `searchPasswords(text query)` | Search Passwords app |

### device

```
#include 'actions/device'
```

| Action | Signature | Description |
|--------|-----------|-------------|
| `getDeviceDetail` | `getDeviceDetail(deviceDetail detail)` | Get device info |
| `getBatteryLevel` | `getBatteryLevel()` | Battery percentage |
| `isCharging` | `isCharging(): bool` | Is device charging? |
| `connectedToCharger` | `connectedToCharger(): bool` | Connected to charger? |
| `getOnScreenContent` | `getOnScreenContent()` | Get on-screen content |
| `getDeviceUsage` | `getDeviceUsage(deviceUsageType ?usageType="all", variable ?device, usageDuration ?during="today", text ?startTime, text ?startTime)` | Screen Time data |
| `getOrientation` | `getOrientation(): text` | Device orientation |
| `vibrate` | `vibrate()` | Haptic vibration |
| `lockScreen` | `lockScreen()` | Lock screen |
| `reboot` | `reboot()` | Reboot device |
| `shutdown` | `shutdown()` | Shut down device |
| `setAirplaneMode` | `setAirplaneMode(bool status)` | Set airplane mode |
| `toggleAirplaneMode` | `toggleAirplaneMode()` | Toggle airplane mode |

Device details: `Device Name`, `Device Hostname`, `Device Model`, `Device Is Watch`, `System Version`, `Screen Width`, `Screen Height`, `Current Volume`, `Current Brightness`, `Current Appearance`

Usage types: `all`, `app`, `website`

Usage durations: `today`, `yesterday`, `lastWeek`, `thisWeek`, `thisMonth`, `thisYear`, `specifiedDay`, `inBetween`

### settings

```
#include 'actions/settings'
```

#### Appearance

| Action | Signature | Description |
|--------|-----------|-------------|
| `darkMode` | `darkMode()` | Set dark mode |
| `lightMode` | `lightMode()` | Set light mode |
| `toggleAppearance` | `toggleAppearance()` | Toggle dark/light |

#### Device Controls

| Action | Signature | Description |
|--------|-----------|-------------|
| `setVolume` | `setVolume(float volume)` | Set volume (0.0-1.0) |
| `setBrightness` | `setBrightness(float brightness)` | Set brightness (0.0-1.0) |

#### Wireless

| Action | Signature | Description |
|--------|-----------|-------------|
| `setWifi` | `setWifi(bool status)` | Enable/disable Wi-Fi |
| `setBluetooth` | `setBluetooth(bool status)` | Enable/disable Bluetooth |
| `toggleWifi` | `toggleWifi()` | Toggle Wi-Fi |
| `toggleBluetooth` | `toggleBluetooth()` | Toggle Bluetooth |
| `setCellularData` | `setCellularData(bool status)` | Enable/disable cellular |
| `toggleCellularData` | `toggleCellularData()` | Toggle cellular |

#### Focus Modes

| Action | Signature | Description |
|--------|-----------|-------------|
| `setFocusMode` | `setFocusMode(focusModes ?focusMode="Do Not Disturb", focusUntil ?until="Turned Off", text ?time, variable ?event)` | Set focus mode |
| `toggleFocusMode` | `toggleFocusMode(focusModes ?focusMode="Do Not Disturb")` | Toggle focus mode |
| `getFocusMode` | `getFocusMode()` | Get current focus mode |
| `DNDOn` | `DNDOn()` | Enable Do Not Disturb |
| `DNDOff` | `DNDOff()` | Disable Do Not Disturb |
| `toggleDND` | `toggleDND()` | Toggle DND |

Focus modes: `Do Not Disturb`, `Personal`, `Work`, `Sleep`, `Driving`

#### Display

| Action | Signature | Description |
|--------|-----------|-------------|
| `setNightShift` | `setNightShift(bool status)` | Night Shift on/off |
| `setTrueTone` | `setTrueTone(bool status)` | True Tone on/off |
| `toggleNightShift` | `toggleNightShift()` | Toggle Night Shift |
| `toggleTrueTone` | `toggleTrueTone()` | Toggle True Tone |

#### Stage Manager

| Action | Signature | Description |
|--------|-----------|-------------|
| `setStageManager` | `setStageManager(bool status, bool ?showDock=true, bool ?showRecentApps=true)` | Set Stage Manager |
| `toggleStageManager` | `toggleStageManager(bool ?showDock=true, bool ?showRecentApps=true)` | Toggle Stage Manager |

#### Wallpaper

| Action | Signature | Description |
|--------|-----------|-------------|
| `setWallpaper` | `setWallpaper(variable input)` | Set wallpaper |
| `getWallpaper` | `getWallpaper()` | Get current wallpaper |
| `getAllWallpapers` | `getAllWallpapers(): array` | Get all wallpapers |

### media

```
#include 'actions/media'
```

#### Shazam

| Action | Signature | Description |
|--------|-----------|-------------|
| `startShazam` | `startShazam(bool ?show=true, bool ?showError=true)` | Listen and identify song |
| `getShazamDetail` | `getShazamDetail(variable input, shazamDetail detail)` | Get song detail |

Shazam details: `Apple Music ID`, `Artist`, `Title`, `Is Explicit`, `Lyrics Snippet`, `Lyric Snippet Synced`, `Artwork`, `Video URL`, `Shazam URL`, `Apple Music URL`, `Name`

#### Camera & Recording

| Action | Signature | Description |
|--------|-----------|-------------|
| `takePhoto` | `takePhoto(number ?count=1, bool ?showPreview=true)` | Take photos |
| `takeVideo` | `takeVideo(cameraOrientation ?camera="Front", videoQuality ?quality="High", recordingStart ?recordingStart="Immediately")` | Record video |
| `recordAudio` | `recordAudio(audioQuality ?quality="Normal", audioStart ?start="On Tap")` | Record audio |
| `takeScreenshot` | `takeScreenshot(bool ?mainMonitorOnly=false)` | Take screenshot |

#### Audio

| Action | Signature | Description |
|--------|-----------|-------------|
| `playSound` | `playSound(variable input)` | Play audio |
| `encodeAudio` | `encodeAudio(variable audio, audioFormats ?format="M4A", audioSpeeds ?speed="Normal")` | Encode audio |

#### Podcasts

| Action | Signature | Description |
|--------|-----------|-------------|
| `searchPodcasts` | `searchPodcasts(text query)` | Search podcasts |
| `getPodcasts` | `getPodcasts()` | Get user's podcasts |
| `playPodcast` | `playPodcast(variable podcast)` | Play a podcast |
| `getPodcastDetail` | `getPodcastDetail(variable podcast, podcastDetail detail)` | Get podcast info |

#### Metadata

| Action | Signature | Description |
|--------|-----------|-------------|
| `setMetadata` | `setMetadata(variable media, variable ?artwork, text ?title, text ?artist, text ?album, text ?genre, text ?year)` | Set media metadata |
| `stripMediaMetadata` | `stripMediaMetadata(variable media)` | Strip metadata |

### location

```
#include 'actions/location'
```

#### Location

| Action | Signature | Description |
|--------|-----------|-------------|
| `currentLocation` | `currentLocation()` | Get current location |
| `getCurrentLocation` | `getCurrentLocation()` | Get current location (alias) |
| `getLocationDetail` | `getLocationDetail(variable location, locationDetail detail)` | Get location detail |
| `streetAddress` | `streetAddress(text line1, text line2, text city, text state, text country, number zipCode)` | Create location |
| `getAddresses` | `getAddresses(variable input)` | Extract addresses |

Location details: `Name`, `URL`, `Label`, `Phone Number`, `Region`, `ZIP Code`, `State`, `City`, `Street`, `Altitude`, `Longitude`, `Latitude`

#### Weather

| Action | Signature | Description |
|--------|-----------|-------------|
| `getCurrentWeather` | `getCurrentWeather(text ?location="Current Location")` | Current weather |
| `getWeatherForecast` | `getWeatherForecast(weatherForecastTypes ?type="Daily", text ?location="Current Location")` | Forecast |
| `getWeatherDetail` | `getWeatherDetail(variable weather, weatherDetail detail)` | Weather detail |
| `addWeatherLocation` | `addWeatherLocation(variable location)` | Add to Weather app |
| `removeWeatherLocation` | `removeWeatherLocation(variable location)` | Remove from Weather app |

Weather details: `Temperature`, `Feels Like`, `High`, `Low`, `Condition`, `Wind Speed`, `Wind Direction`, `Humidity`, `Dewpoint`, `Pressure`, `Visibility`, `UV Index`, `Sunrise Time`, `Sunset Time`, `Precipitation Chance`, `Precipitation Amount`, `Air Quality Index`, `Air Quality Category`, `Air Pollutants`, `Date`, `Location`, `Name`

Forecast types: `Daily`, `Hourly`

#### Maps

| Action | Signature | Description |
|--------|-----------|-------------|
| `openInMaps` | `openInMaps(variable location)` | Open in Maps |
| `getMapsLink` | `getMapsLink(variable location)` | Get Maps URL |
| `getHalfwayPoint` | `getHalfwayPoint(variable firstLocation, variable secondLocation)` | Halfway point |

### text

```
#include 'actions/text'
```

#### Speech & Dictation

| Action | Signature | Description |
|--------|-----------|-------------|
| `listen` | `listen(stopListeningTrigger ?stopListening="After Pause", language ?language): text` | Dictation input |
| `speak` | `speak(text prompt, bool ?waitUntilFinished=true, text ?language)` | Text-to-speech |
| `makeSpokenAudio` | `makeSpokenAudio(text text, number ?rate, number ?pitch)` | Create spoken audio file |
| `transcribeText` | `transcribeText(variable audio): text` | Transcribe audio to text |

Stop listening triggers: `After Pause`, `After Short Pause`, `On Tap`

#### Text Operations

| Action | Signature | Description |
|--------|-----------|-------------|
| `define` | `define(text word): text` | Dictionary definition |
| `getText` | `getText(variable input): text` | Get text from input |
| `getTextFromImage` | `getTextFromImage(variable image): text` | OCR from image |
| `getEmojiName` | `getEmojiName(text emoji): text` | Get emoji name |
| `joinText` | `joinText(variable text, text ?glue="\n"): text` | Join text |
| `containsText` | `containsText(text subject, text text, bool ?caseSensitive=true)` | Check text contains |
| `correctSpelling` | `correctSpelling(text text): text` | Correct spelling |
| `capitalize` | `capitalize(text text): text` | Sentence case |
| `capitalizeAll` | `capitalizeAll(text text): text` | Title Case |
| `lowercase` | `lowercase(text text): text` | Lowercase |
| `alternatingCase` | `alternatingCase(text text): text` | aLtErNaTiNg CaSe |

#### Regular Expressions

| Action | Signature | Description |
|--------|-----------|-------------|
| `matchText` | `matchText(text regexPattern, text text, bool ?caseSensitive=true)` | Regex match |
| `getMatchGroup` | `getMatchGroup(variable matches, number index)` | Get match group |
| `getMatchGroups` | `getMatchGroups(variable matches)` | Get all match groups |

#### Rich Text

| Action | Signature | Description |
|--------|-----------|-------------|
| `getRichTextFromMarkdown` | `getRichTextFromMarkdown(text markdown): text` | Markdown to rich text |
| `getRichTextFromHTML` | `getRichTextFromHTML(text html): text` | HTML to rich text |
| `makeMarkdown` | `makeMarkdown(text richText): text` | Rich text to Markdown |
| `makeHTML` | `makeHTML(text input, bool ?makeFullDocument=false): text` | Rich text to HTML |

### sharing

```
#include 'actions/sharing'
```

| Action | Signature | Description |
|--------|-----------|-------------|
| `setClipboard` | `setClipboard(variable value, bool ?local=false, text ?expire)` | Set clipboard |
| `getClipboard` | `getClipboard()` | Get clipboard |
| `share` | `share(variable input)` | Share sheet |
| `airdrop` | `airdrop(variable input)` | AirDrop |
| `sendMessage` | `sendMessage(variable contact, text message, bool ?prompt=true)` | Send iMessage/SMS |
| `sendEmail` | `sendEmail(variable contact, text from, text subject, text body, bool ?prompt=true, bool ?draft=false)` | Send email |
| `findMessage` | `findMessage(text search)` | Find message |
| `findConversation` | `findConversation(text search)` | Find conversation |
| `findEmail` | `findEmail(text search)` | Find email |

### shortcuts

```
#include 'actions/shortcuts'
```

| Action | Signature | Description |
|--------|-----------|-------------|
| `run` | `run(text shortcutName, variable input)` | Run another shortcut |
| `runSelf` | `runSelf(variable output)` | Re-run current shortcut |
| `getShortcuts` | `getShortcuts(): array` | List all shortcuts |
| `searchShortcuts` | `searchShortcuts(text query)` | Search shortcuts |
| `openShortcut` | `openShortcut(text shortcutName)` | Open in editor |
| `makeShortcut` | `makeShortcut(text name, bool ?open=true)` | Create new shortcut |
| `getShortcutDetail` | `getShortcutDetail(variable shortcut, shortcutDetail detail)` | Get shortcut info |
| `createShortcutLink` | `createShortcutLink(variable shortcut)` | Create sharing link |

---

## 5. Patterns & Recipes

### Pattern 1: API Call + ChatGPT Analysis

Fetch data from an API, then send it to ChatGPT for interpretation. Always hardcode URLs inline.

```cherri
#include 'actions/web'
#include 'actions/scripting'
#include 'actions/intelligence'

#define name API Analysis
#define color teal
#define glyph binoculars

const data = downloadURL("https://api.example.com/data", {"Authorization": "Bearer my-token-here"})
const dict = getDictionary(data)
const value = getValue(dict, "key")

const analysis = askChatGPT("Analyze this data: {value}. Summarize in 3 sentences.")
show(analysis)
```

Real example from `whats-next-book.cherri`:

```cherri
#include 'actions/web'
#include 'actions/scripting'
#include 'actions/intelligence'

#define name Whats Next Book
#define color teal
#define glyph openBook

const listening = downloadURL("https://weixiangs-mac-mini.tail1ef495.ts.net/currently-listening", {"X-Bridge-Key": "YOUR_BRIDGE_KEY_HERE"})
const pick = jsonRequest("https://weixiangs-mac-mini.tail1ef495.ts.net/random-book?unstarted=true", "POST", {}, {"X-Bridge-Key": "YOUR_BRIDGE_KEY_HERE"})

const rec = askChatGPT("You are an audiobook concierge. Current books: {listening} Random unstarted: {pick} -- Recommend what to listen to next in under 60 words.")
show(rec)
```

### Pattern 2: Multi-LLM Debate

Use multiple LLM backends (on-device, ChatGPT, Cloud) for different perspectives on the same topic.

```cherri
#include 'actions/intelligence'
#include 'actions/text'

#define name AI Debate Club
#define color red
#define glyph microphone

const topic = listen("After Pause")

const forArg = askDeviceLLM("Argue FOR: {topic} in 3-4 sentences.")
const againstArg = askChatGPT("Argue AGAINST: {topic} in 3-4 sentences.")

const forPoints = generateKeyPoints(forArg)
const againstPoints = generateKeyPoints(againstArg)

const verdict = askCloudLLM("Judge this debate. FOR: {forArg} AGAINST: {againstArg}. Pick winner, explain in 2 sentences, score each out of 10.")
const polished = adjustTextTone(verdict, "professional")

speak(polished)
show("FOR: {forArg}\nAGAINST: {againstArg}\nVerdict: {polished}")
```

### Pattern 3: Sensor Data + AI Interpretation

Collect device/weather/location data, then ask AI to interpret it.

```cherri
#include 'actions/location'
#include 'actions/device'
#include 'actions/settings'
#include 'actions/intelligence'

#define name Weather Commander
#define color blue
#define glyph cloud

const weather = getCurrentWeather()
const temp = getWeatherDetail(weather, "Temperature")
const condition = getWeatherDetail(weather, "Condition")
const humidity = getWeatherDetail(weather, "Humidity")
const uv = getWeatherDetail(weather, "UV Index")

const battery = getBatteryLevel()
const loc = currentLocation()
const city = getLocationDetail(loc, "City")

const summary = "City: {city}, Temp: {temp}, Condition: {condition}, Humidity: {humidity}, UV: {uv}, Battery: {battery}%"
const briefing = askChatGPT("Morning briefing from this data. Include outfit suggestion, UV warning if needed. Data: {summary}")

setVolume(0.5)
speak(briefing)
showNotification("Briefing complete.", "Weather Commander")
```

### Pattern 4: Shazam + Metadata + AI

Identify a song, extract all metadata, then ask AI for analysis.

```cherri
#include 'actions/media'
#include 'actions/intelligence'
#include 'actions/text'

#define name Shazam DJ
#define color pink
#define glyph musicNote

const song = startShazam()
const title = getShazamDetail(song, "Title")
const artist = getShazamDetail(song, "Artist")
const lyrics = getShazamDetail(song, "Lyrics Snippet")
const artwork = getShazamDetail(song, "Artwork")

const analysis = askChatGPT("Analyze: {title} by {artist}. Lyrics: {lyrics}. Give genre, mood, BPM estimate, 3 similar artists.")
const friendly = adjustTextTone(analysis, "friendly")

speak("Now playing: {title} by {artist}.")
show("Song: {title}\nArtist: {artist}\n\n{friendly}")
```

### Pattern 5: Voice Input + AI Research Pipeline

Capture voice, run through multiple AI stages (research, flash cards, summary).

```cherri
#include 'actions/intelligence'
#include 'actions/text'

#define name Voice Researcher
#define color blue
#define glyph microphone

const spoken = listen()

const research = askChatGPT("Deep research: {spoken}. Key concepts, related topics, counterarguments, study guide.")
const flashCards = askDeviceLLM("Create 5 flash cards from: {research}. Format: Q: / A:")
const keyPoints = generateKeyPoints(research)
const summary = generateSummary(research)
const proSummary = adjustTextTone(summary, "professional")
const flashTable = generateTable(flashCards)

speak(proSummary)
show("TOPIC: {spoken}\n\nSUMMARY: {proSummary}\n\nKEY POINTS: {keyPoints}\n\nFLASH CARDS: {flashTable}")
```

### Pattern 6: Sub-Shortcut Composition with run()

Call other shortcuts as functions and use their output.

```cherri
#include 'actions/shortcuts'
#include 'actions/intelligence'
#include 'actions/sharing'

#define name Market Report
#define color darkorange
#define glyph binoculars

const formatInstructions = "Format as: header, sentiment, index snapshot, key moves..."
const econData = run("_economic Cal Pull", formatInstructions)
const earningsData = run("Earnings Pull", formatInstructions)

const report = askChatGPT("Create market report from: {econData} and {earningsData}")
setClipboard(report)
showNotification("Report ready.", "Market Report")
```

### Pattern 7: Drafts App Integration via rawAction

Send output to Drafts 5 using the raw action interface.

```cherri
rawAction("com.agiletortoise.Drafts5.CaptureIntent", {
    "AppIntentDescriptor": "",
    "ShowWhenRun": false,
    "content": "{myContent}",
    "tags": ["Shortcuts_automation", "My_tag"]
})
```

`rawAction` lets you call any iOS App Intent by its identifier, even ones Cherri does not have built-in support for. The second argument is a dictionary of the intent's parameters.

### Pattern 8: Poll-and-Wait for Async Jobs

POST a job, then poll until done with a timeout.

```cherri
#include 'actions/web'
#include 'actions/scripting'
#include 'actions/text'

const spoken = listen()
const resp = jsonRequest("https://example.com/v1/intent", "POST", {"text": "{spoken}"}, {"Authorization": "Bearer my-token"})
const dict = getDictionary(resp)
const jobId = getValue(dict, "job_id")

repeat i for 8 {
    wait(3)
    const poll = downloadURL("https://example.com/v1/jobs/{jobId}", {"Authorization": "Bearer my-token"})
    const pollDict = getDictionary(poll)
    const status = getValue(pollDict, "status")
    if status == "done" {
        const result = getValue(pollDict, "result")
        show("{result}")
        output("")
    }
}

show("Job {jobId} still pending.")
```

### Pattern 9: Menu-Driven Multi-Phase Shortcut

Use `menu` blocks for branching user interfaces.

```cherri
menu "My Assistant" {
    item "Option A":
        // actions for option A
        show("You picked A")

    item "Option B":
        // actions for option B
        show("You picked B")

    item "Dashboard":
        // fetch and display data
        const data = downloadURL("https://example.com/status", {})
        show(data)
}
```

---

## 6. Import from iCloud

### Decompiling Existing Shortcuts

You can reverse-engineer any shared iCloud shortcut into Cherri source:

```bash
~/go/bin/cherri --import=https://www.icloud.com/shortcuts/abc123def456
```

This downloads the shortcut, decompiles it, and outputs `.cherri` source code. Use this to:
- Learn how complex shortcuts are structured
- Adapt patterns from community shortcuts
- Understand action signatures you have not used before

### Import from local .shortcut file

```bash
~/go/bin/cherri --import=/path/to/file.shortcut
```

### Options

- Add `-c` / `--comments` to include comment actions in the import
- The imported source will use Cherri syntax and can be recompiled

---

## 7. Testing Protocol

### Compile

```bash
cd /path/to/shortcuts/generated
~/go/bin/cherri my-shortcut.cherri
```

Verify the `.shortcut` file was created:

```bash
ls -la my-shortcut.shortcut
```

### Clear Saved State Before Testing

If Shortcuts is crash-looping or behaving strangely:

```bash
rm -rf ~/Library/Saved\ Application\ State/com.apple.shortcuts.savedState
```

### Import Test Sequence

Open one shortcut at a time. The bash one-liner with delay:

```bash
for f in *.shortcut; do echo "Opening $f..."; open "$f"; sleep 5; done
```

The 5-second delay gives Shortcuts time to finish importing before the next file arrives.

### One Shortcut at a Time Rule

Never batch-open shortcuts. If you need to test multiple shortcuts:

1. Open one `.shortcut` file
2. Wait for it to appear in the Shortcuts app
3. Close the import dialog
4. Open the next one

### Compilation Flags for Testing

```bash
# Normal compilation (signed, contacts-only)
~/go/bin/cherri my-shortcut.cherri

# Skip signing (faster, for compilation testing only)
~/go/bin/cherri my-shortcut.cherri --skip-sign

# Debug mode (outputs .plist and preprocessed file)
~/go/bin/cherri my-shortcut.cherri -d

# Include comments in compiled output
~/go/bin/cherri my-shortcut.cherri -c
```

### Verify Before Running Cherri

Always verify you are not about to overwrite a directory:

```bash
# Check the target is a file, not a directory
test -f my-shortcut.cherri && echo "OK: is a file" || echo "DANGER: not a file"

# Check you are in the right directory
pwd
ls *.cherri
```

---

## Appendix: Language Syntax Quick Reference

### Header Directives

```cherri
#define name My Shortcut Name
#define glyph gear
#define color blue
```

Available colors: `red`, `orange`, `darkorange`, `yellow`, `green`, `teal`, `blue`, `purple`, `pink`, `gray`

Glyphs: `gear`, `microphone`, `barGraph`, `globe`, `bell`, `book`, `openBook`, `camera`, `cloud`, `doc`, `flag`, `heart`, `house`, `link`, `lock`, `magnifyingglass`, `music`, `musicNote`, `pencil`, `person`, `phone`, `play`, `star`, `tag`, `binoculars`, `brain`, `dice`, `headphones`

### Variables

```cherri
const immutable = "value"         // Immutable (const)
var mutable = "value"             // Mutable (var)
@shorthand = "value"              // Mutable shorthand
```

### String Interpolation

```cherri
const name = "World"
show("Hello {name}")              // Variable interpolation with {varName}
```

### Control Flow

```cherri
// If/else
if status == "done" {
    show("Done!")
} else {
    show("Not done")
}

// Repeat
repeat i for 10 {
    wait(1)
}

// Menu
menu "Title" {
    item "Choice A":
        show("A")
    item "Choice B":
        show("B")
}
```

### rawAction

For calling any iOS action not built into Cherri:

```cherri
rawAction("com.example.AppIntent", {
    "param1": "value1",
    "param2": "value2"
})
```

### All Available Action Categories for --docs

`basic`, `a11y`, `calendar`, `contacts`, `crypto`, `device`, `documents`, `dropbox`, `images`, `location`, `intelligence`, `mac`, `math`, `media`, `music`, `network`, `pdf`, `photos`, `scripting`, `settings`, `sharing`, `shortcuts`, `text`, `translation`, `web`

Run `~/go/bin/cherri --docs=<category>` to see full documentation for any category not covered in depth above.
