from generate_test_client import client
from jsonschema import validate

def test_fetch_version_success():
    response = client.post("/audio_query?text=こんにちは&speaker=0")
    assert response.status_code == 200

    schema = {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "PyJsonValidate",
      "description": "audio query validation",
      "type": "object",
      "properties" :{
        "accent_phrases": {
          "type": "array",
          "minItems": 1,
          "maxItems": 1,
          "items": {
            "type": "object",
            "properties": {
              "moras": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                  "type": "object",
                  "properties": {
                    "text": {
                      "type": "string",
                      "minLength": 1,
                      "maxLength": 1,
                    },
                    "consonant": {
                      "type": ["string", "null"],
                      "pattern": "^[knw]|(ch)$",
                    },
                    "consonant_length": {
                      "type": ["number", "null"],
                    },
                    "vowel": {
                      "type": ["string", "null"],
                      "pattern": "^[oNia]$",
                    },
                    "vowel_length": {
                      "type": ["number", "null"],
                    },
                    "pitch": {
                      "type": "number",
                    },
                  },
                },
              },
              "accent": {
                "type": "number",
              },
              "pause_mora": {
                "type": "null",
              },
              "is_interrogative": {
                "type": "boolean",
              },
            },
          },
        },
        "speedScale": {
          "type": "number",
        },
        "pitchScale": {
          "type": "number",
        },
        "intonationScale": {
          "type": "number",
        },
        "volumeScale": {
          "type": "number",
        },
        "prePhonemeLength": {
          "type": "number",
        },
        "postPhonemeLength": {
          "type": "number",
        },
        "outputSampleRate": {
            "type": "number",
        },
        "outputStereo": {
          "type": "boolean",
        },
        "kana": {
          "type": "string",
        },
      },
    }
    validate(response.json(), schema)
