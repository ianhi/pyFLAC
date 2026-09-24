# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#  pyFLAC decoder test suite
#
#  Copyright (c) 2020-2024, Sonos, Inc.
#  All rights reserved.
#
# ------------------------------------------------------------------------------

import io
import os
import pathlib
import tempfile
import time
import unittest

import numpy as np
import soundfile as sf
from pyflac.decoder import _Decoder
from pyflac import (
    FileDecoder,
    StreamDecoder,
    OneShotDecoder,
    DecoderState,
    DecoderInitException,
    DecoderProcessException,
    StreamEncoder,
)


class TestDecoder(unittest.TestCase):
    """
    Test Suite for the generic decoder class
    """
    def setUp(self):
        self.decoder = _Decoder()

    def test_state(self):
        """ Test that the state returns a valid string """
        self.assertEqual(self.decoder.state, DecoderState.UNINITIALIZED)
        self.assertEqual(str(self.decoder.state), 'FLAC__STREAM_DECODER_UNINITIALIZED')


class TestStreamDecoder(unittest.TestCase):
    """
    Test suite for the stream decoder class.
    """
    def setUp(self):
        self.decoder = None
        self.write_callback_called = False
        self.tests_path = pathlib.Path(__file__).parent.absolute()

    def _write_callback(self, data, rate, channels, samples):
        assert isinstance(data, np.ndarray)
        assert isinstance(rate, int)
        assert isinstance(channels, int)
        assert isinstance(samples, int)
        self.write_callback_called = True

    def test_process_invalid_data(self):
        """ Test that processing invalid data raises an exception """
        test_data = bytearray(os.urandom(100000))

        with self.assertRaises(DecoderProcessException):
            self.decoder = StreamDecoder(write_callback=self._write_callback)
            self.decoder.process(test_data)
            self.decoder.finish()

    def test_process(self):
        """ Test that FLAC data can be decoded """
        test_path = self.tests_path / 'data/stereo.flac'
        with open(test_path, 'rb') as flac:
            test_data = flac.read()

        self.decoder = StreamDecoder(write_callback=self._write_callback)
        time.sleep(0.05)

        self.decoder.process(test_data)
        self.decoder.finish()
        self.assertTrue(self.write_callback_called)
        self.assertFalse(self.decoder._thread.is_alive())

    def test_process_24_bit(self):
        """ Test that 24-bit FLAC data is decoded to right-aligned int32 samples """
        flac = io.BytesIO()
        test_samples = np.random.randint(-2**23, 2**23, (4096, 2), dtype='int32')
        sf.write(flac, test_samples << 8, 44100, format='FLAC', subtype='PCM_24')

        decoded = []
        self.decoder = StreamDecoder(write_callback=lambda data, *args: decoded.append(data))
        self.decoder.process(flac.getvalue())
        self.decoder.finish()

        output = np.concatenate(decoded)
        self.assertEqual(output.dtype, np.int32)
        np.testing.assert_array_equal(output, test_samples)

    def test_process_blocks(self):
        """ Test that FLAC data can be decoded in blocks """
        blocksize = 1024
        test_path = self.tests_path / 'data/stereo.flac'
        with open(test_path, 'rb') as flac:
            test_data = flac.read()
            data_length = len(test_data)

        self.decoder = StreamDecoder(write_callback=self._write_callback)
        for i in range(0, data_length - blocksize, blocksize):
            self.decoder.process(test_data[i:i + blocksize])

        self.decoder._done = True


class TestFileDecoder(unittest.TestCase):
    """
    Test suite for the file decoder class.
    """
    def setUp(self):
        self.decoder = None
        self.callback_called = False
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.wav')
        self.default_kwargs = {'input_file': None}

    def test_process_invalid_file(self):
        """ Test that an invalid file raises an error """
        self.default_kwargs['input_file'] = pathlib.Path('invalid.flac')
        with self.assertRaises(DecoderInitException):
            self.decoder = FileDecoder(**self.default_kwargs)

    def test_process_8bit_file(self):
        """ Test that an 8-bit FLAC file is decoded losslessly """
        test_file = pathlib.Path(__file__).parent / 'data/8bit.flac'
        self.default_kwargs['input_file'] = test_file
        self.default_kwargs['output_file'] = pathlib.Path(self.temp_file.name)
        self.decoder = FileDecoder(**self.default_kwargs)
        data, _ = self.decoder.process()
        np.testing.assert_array_equal(data, sf.read(test_file, always_2d=True)[0])

    def test_process_24_bit_file(self):
        """ Test that a 24-bit FLAC file is decoded to a 24-bit WAV file """
        flac_file = tempfile.NamedTemporaryFile(suffix='.flac')
        test_samples = np.random.randint(-2**23, 2**23, (1024, 2), dtype='int32') << 8
        sf.write(flac_file.name, test_samples, 44100, subtype='PCM_24')
        self.default_kwargs['input_file'] = pathlib.Path(flac_file.name)
        self.default_kwargs['output_file'] = pathlib.Path(self.temp_file.name)
        self.decoder = FileDecoder(**self.default_kwargs)
        self.decoder.process()

        self.assertEqual(sf.info(self.temp_file.name).subtype, 'PCM_24')
        np.testing.assert_array_equal(sf.read(self.temp_file.name, dtype='int32')[0], test_samples)

    def test_process_20_bit_file(self):
        """ Test that a 20-bit FLAC file is decoded to a 24-bit WAV file """
        flac_file = tempfile.NamedTemporaryFile(suffix='.flac')
        test_samples = np.random.randint(-2**19, 2**19, (1024, 2), dtype='int32')
        with open(flac_file.name, 'wb') as flac:
            encoder = StreamEncoder(sample_rate=44100, write_callback=lambda buffer, *args: flac.write(buffer),
                                    seek_callback=flac.seek, tell_callback=flac.tell, bits_per_sample=20)
            encoder.process(test_samples)
            encoder.finish()
        self.default_kwargs['input_file'] = pathlib.Path(flac_file.name)
        self.default_kwargs['output_file'] = pathlib.Path(self.temp_file.name)
        self.decoder = FileDecoder(**self.default_kwargs)
        self.decoder.process()

        self.assertEqual(sf.info(self.temp_file.name).subtype, 'PCM_24')
        np.testing.assert_array_equal(sf.read(self.temp_file.name, dtype='int32')[0] >> 12, test_samples)

    def test_process_mono_file(self):
        """ Test that a mono FLAC file can be processed """
        test_file = pathlib.Path(__file__).parent / 'data/mono.flac'
        self.default_kwargs['input_file'] = test_file
        self.default_kwargs['output_file'] = pathlib.Path(self.temp_file.name)
        self.decoder = FileDecoder(**self.default_kwargs)
        self.assertIsNotNone(self.decoder.process())

    def test_process_stereo_file(self):
        """ Test that a stereo FLAC file can be processed """
        test_file = pathlib.Path(__file__).parent / 'data/stereo.flac'
        self.default_kwargs['input_file'] = test_file
        self.default_kwargs['output_file'] = pathlib.Path(self.temp_file.name)
        self.decoder = FileDecoder(**self.default_kwargs)
        self.assertIsNotNone(self.decoder.process())

    def test_process_5_1_surround_file(self):
        """ Test that a 5.1 surround FLAC file can be processed """
        test_file = pathlib.Path(__file__).parent / 'data/surround.flac'
        self.default_kwargs['input_file'] = test_file
        self.default_kwargs['output_file'] = pathlib.Path(self.temp_file.name)
        self.decoder = FileDecoder(**self.default_kwargs)
        self.assertIsNotNone(self.decoder.process())

    def test_process_32_bit_file(self):
        """ Test that a 32-bit FLAC file can be processed """
        test_file = pathlib.Path(__file__).parent / 'data/32bit.flac'
        self.default_kwargs['input_file'] = test_file
        self.default_kwargs['output_file'] = pathlib.Path(self.temp_file.name)
        self.decoder = FileDecoder(**self.default_kwargs)
        self.assertIsNotNone(self.decoder.process())
        self.assertEqual(sf.info(self.temp_file.name).subtype, 'PCM_32')


class TestOneShotDecoder(unittest.TestCase):
    """
    Test suite for the one-shot decoder class.
    """
    def setUp(self):
        self.decoder = None
        self.write_callback_called = False
        self.tests_path = pathlib.Path(__file__).parent.absolute()

    def _write_callback(self, data, rate, channels, samples):
        assert isinstance(data, np.ndarray)
        assert isinstance(rate, int)
        assert isinstance(channels, int)
        assert isinstance(samples, int)
        self.write_callback_called = True

    def test_process(self):
        """ Test that FLAC data can be decoded """
        test_path = self.tests_path / 'data/stereo.flac'
        with open(test_path, 'rb') as flac:
            test_data = flac.read()

        self.decoder = OneShotDecoder(write_callback=self._write_callback, buffer=test_data)
        self.assertTrue(self.write_callback_called)


if __name__ == '__main__':
    unittest.main(failfast=True)
