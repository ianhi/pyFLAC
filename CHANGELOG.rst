pyFLAC Changelog
----------------

**Unreleased**

* Added support for bit depths other than 16 and 32, including 24-bit
  (see `#17 <https://github.com/sonos/pyFLAC/discussions/17>`_).

  * Decoded audio up to 16-bit is returned as `int16`, and above that as
    `int32`, with samples right-aligned. 8-bit FLAC files no longer raise an
    error.
  * The `StreamEncoder` takes a `bits_per_sample` argument, for audio held in a
    wider data type than its bit depth, such as 24-bit audio in an `int32` array.
  * The `FileEncoder` accepts PCM_U8 and PCM_24 WAV files.

* Fixed the `FileDecoder` writing 32-bit audio to a 16-bit WAV file.

**v3.0.0**

* Fixed bug in the shutdown behaviour of the `StreamDecoder` (see #22 and #23).
* Automatically detect bit depth of input data in the `FileEncoder`, and
  raise an error if not 16-bit or 32-bit PCM (see #24).
* Added a new `OneShotDecoder` to decode a buffer of FLAC data in a single
  blocking operation, without the use of threads. Courtesy of @GOAE.

**v2.2.0**

* Updated FLAC library to v1.4.3.
    See `FLAC Changelog <https://xiph.org/flac/changelog.html>`_.
* Added support for `int32` data
* Added `limit_min_bitrate` property.
* Removed support for Python 3.7

**v2.1.0**

* Added support for Linux `arm64` architectures
* Added support for Darwin `arm64` architectures (macOS Apple Silicon)
* Fixed Raspberry Pi Zero library (see #13)
* Updated FLAC library to v1.3.4

**v2.0.0**

* Added `seek` and `tell` callbacks to `StreamEncoder`
* Renamed the write callbacks from `callback` to `write_callback` for `StreamEncoder` and `StreamDecoder`

**v1.0.0**

* Added a `StreamEncoder` to compress raw audio data on-the-fly into a FLAC byte stream
* Added a `StreamDecoder` to decompress a FLAC byte stream back to raw audio data
* Added a `FileEncoder` to convert a WAV file to FLAC encoded data, optionally saving to a FLAC file
* Added a `FileDecoder` to convert a FLAC file to raw audio data, optionally saving to a WAV file
* Bundled with libFLAC version 1.3.3
