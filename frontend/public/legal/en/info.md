# RadioHub - Technical Information

This manual explains the key concepts, technical terms, and limitations of RadioHub. It helps you understand why certain features work the way they do.

---

## Playback Modes

### HLS Mode (Default)

HLS stands for "HTTP Live Streaming". RadioHub converts the radio stream via the backend into small segments that the browser can play. This enables:

- **Timeshift:** Rewind within the running program
- **Pause and Resume:** The buffer continues in the background
- **Buffer Recording:** Record previously heard content (HLS-REC)
- **Bitrate Control:** Automatic adaptation to the connection

The HLS buffer is maintained in the backend. The size can be configured under [Settings > General](#/setup/allgemein/einstellungen) (Timeshift Buffer).

### Direct Mode

In Direct mode, the browser connects directly to the station's original stream. This is more resource-efficient but without timeshift, pause, or buffer recording. Useful for servers that don't support HLS conversion.

---

## Badges in the Station List

### ICY (green / gray)

**ICY** stands for "Icecast Metadata" - a protocol that allows radio stations to send the current title within the stream. When a station supports ICY, RadioHub displays the current title and can automatically split recordings into individual songs.

- **ICY (green, "good"):** The station provides precise title change timestamps. Cuts will be clean.
- **ICY (green, "poor"):** The station provides ICY data, but the timestamps are inaccurate (e.g., delayed reports). Cuts may have overlaps or gaps.
- **ICY (gray):** ICY is present but quality has not been rated yet. Click to toggle between "good" and "poor".

**Why does this matter?** Some stations report the new title only seconds after the actual change. RadioHub uses byte positions in the audio stream for cut calculation, but if the station reports late, the cut will be off.

### AD Badges (Ad Detection)

RadioHub can check stations for ads. The check can be started under [Setup > Radio > Stations](#/setup/radio/sender) and analyzes stream URLs and server responses:

- **0% AD (green):** No ad suspicion after check
- **XX% AD (yellow):** Percentage suspicion (e.g., "35% AD") - threshold configurable
- **AD (red):** Manually marked as ad (hidden)
- **OK (blue):** Manually approved despite suspicion

---

## Recording System

### Segmented Recording

RadioHub records in 30-minute segments. If the connection to the station drops, at most the current segment is lost - not the entire recording. For an 8-hour recording, that would be at most 30 minutes instead of everything. Recording settings (format, bitrate, folder) under [Setup > Recordings](#/setup/aufnahmen).

### Stall Detection

During a recording, RadioHub monitors the file size. If the file doesn't grow for 30 seconds, the recording process is detected as "stalled" and restarted. This prevents silent recordings where FFmpeg is running but no longer receiving data.

### ICY Title Split

If a station has ICY metadata, the 30-minute segments are automatically split into individual songs based on detected title changes after recording. Without ICY, the 30-minute blocks remain as segments.

### HTTPS Streams and Reconnect

Many stations use HTTPS. FFmpeg's built-in reconnect function only works reliably with HTTP streams. Therefore, RadioHub handles monitoring and restart on connection drops itself, regardless of protocol.

---

## Timeshift and Buffer

### How Does Timeshift Work?

The backend maintains a rolling buffer of audio segments. Each segment is a few seconds long. The browser requests these segments via HLS playlist. When rewinding, older segments are loaded from the buffer.

### Buffer Recording (HLS-REC)

Buffer recording uses the existing HLS buffer. When you start a recording, RadioHub can include the last X minutes from the buffer. The lookback period is configurable under [Settings > General](#/setup/allgemein/einstellungen) (HLS Recording). This allows recording a song that is already playing.

---

## Cutter (Editing Tool)

### Waveform

The waveform display is calculated from the audio data (peak values). It shows the volume over time and helps with precise placement of cut points.

### Markers

Markers are cut points in the waveform. They can be set manually or automatically taken from ICY title changes. When cutting, the recording is split at these points into segments.

### Transition Analysis

The analysis examines the audio areas around each marker. It evaluates whether the transition is clean (silence between titles) or problematic (e.g., crossfade where two titles overlap). Colors: Green = good, Yellow = check, Red = problematic.

### Normalization (EBU R128)

Normalization adjusts the volume to the EBU R128 standard - the European broadcast standard for consistent loudness. This way all segments sound equally loud, regardless of the station's original volume.

---

## Podcast System

### Auto-Download

Subscribed podcasts can automatically download new episodes. The interval is configurable under [Setup > Podcast](#/setup/podcast). Downloads are stored locally and available offline.

### Feed Update

Podcast feeds are queried via RSS/Atom. The [update interval](#/setup/podcast) determines how often RadioHub checks for new episodes.

---

## Storage and Data

Under [Setup > Storage](#/setup/speicher), the storage paths for recordings, podcasts, and cache can be configured. The display shows used and free space per zone.

External data sources (Radio-Browser API, Podcast Index) are visible under [Setup > Services](#/setup/dienste) and can be switched to your own instances if needed.

---

## Automatic Background Processes

RadioHub runs several processes in the background that work without user interaction:

### Podcast Feed Update

When RadioHub starts, a periodic background process is launched that automatically checks all subscribed podcast feeds for new episodes. The interval (default: 6 hours) is configurable under [Setup > Podcast](#/setup/podcast). With auto-download enabled, new episodes are downloaded automatically.

### HLS Buffer Management

As soon as a station is played in HLS mode, the backend starts an FFmpeg process that splits the audio stream into short segments (1 second each). These form a rolling 10-minute buffer. In parallel, an ICY metadata logger runs that detects title changes in the stream. Both processes end automatically when playback is stopped.

### Recording Monitoring

During an active recording, two monitoring processes run:

- **Stall Detection:** Every 30 seconds, it checks whether the recording file is growing. Three consecutive checks without growth (90 seconds) trigger a restart of the recording process.
- **Storage Monitoring:** Free disk space is checked regularly. If it falls below 100 MB, the recording is automatically stopped to prevent data loss.

### HLS Buffer Recording (HLS-REC)

During an HLS buffer recording, a collector process copies new segments from the HLS buffer to the recording directory every 0.5 seconds. At start, the configured lookback minutes are additionally taken from the existing buffer. On stop, segments are automatically merged and split into individual titles if ICY data is available.

### Favicon Cache

When loading the station list, missing station icons are downloaded in the background and cached locally. This process runs silently and doesn't affect the interface.

### Bitrate Detection

When playing a station for the first time, RadioHub checks the actual bitrate and codec via FFprobe. The result is saved and displayed in the station list. Under [Setup > Radio > Stations](#/setup/radio/sender), a bulk check for all stations can be started.

---

## Known Limitations

- **Timeshift only in HLS mode:** Direct streams are passed through 1:1, without buffering.
- **ICY quality varies:** Some stations deliver inaccurate or delayed metadata. This affects cut accuracy.
- **SSL certificates:** Some stations use unusual SSL configurations. RadioHub works around this when needed, but warnings may occur.
- **Long recordings:** During connection drops, at most 30 minutes are lost (one segment). Older segments are preserved.
- **Browser limitations:** The Web Audio API in the browser can only provide VU meter data when the audio context is active. Some browsers require user interaction for this.

---

## Further Reading

For the technically curious - the technologies and standards behind RadioHub:

### Streaming Protocols

- [HTTP Live Streaming (HLS)](https://en.wikipedia.org/wiki/HTTP_Live_Streaming) - Apple's adaptive streaming protocol used by RadioHub for timeshift
- [Icecast](https://en.wikipedia.org/wiki/Icecast) - Open-source streaming server that popularized the ICY metadata protocol
- [SHOUTcast / ICY Protocol](https://en.wikipedia.org/wiki/SHOUTcast) - Origin of the ICY metadata standard for title information in streams
- [Internet Radio](https://en.wikipedia.org/wiki/Internet_radio) - General overview of radio streaming on the internet

### Audio Formats and Codecs

- [MP3 (MPEG-1 Audio Layer 3)](https://en.wikipedia.org/wiki/MP3) - The most common audio format for radio streams
- [AAC (Advanced Audio Coding)](https://en.wikipedia.org/wiki/Advanced_Audio_Coding) - More modern codec with better quality at the same bitrate
- [Ogg Vorbis](https://en.wikipedia.org/wiki/Vorbis) - Free, open audio codec
- [FLAC (Free Lossless Audio Codec)](https://en.wikipedia.org/wiki/FLAC) - Lossless compression for highest quality

### Audio Processing

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - European standard for loudness normalization in broadcasting
- [FFmpeg](https://en.wikipedia.org/wiki/FFmpeg) - The central multimedia framework used by RadioHub for conversion, recording, and cutting
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Browser interface for audio analysis (VU meter, waveform)

### Data Sources

- [Radio-Browser API](https://www.radio-browser.info/) - Open community database with over 30,000 radio stations worldwide
- [Podcast Index](https://podcastindex.org/) - Open podcast catalog as an alternative to proprietary directories
- [RSS (Really Simple Syndication)](https://en.wikipedia.org/wiki/RSS) - The feed format through which podcasts provide new episodes

### Technical Fundamentals

- [Bitrate](https://en.wikipedia.org/wiki/Bit_rate) - Data rate of an audio stream (e.g., 128 kbps, 320 kbps)
- [Streaming Media](https://en.wikipedia.org/wiki/Streaming_media) - Fundamentals of real-time data transmission
- [Audio Data Compression](https://en.wikipedia.org/wiki/Audio_coding_format) - How lossy compression works
- [SSL/TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security) - Encryption used in HTTPS streams
