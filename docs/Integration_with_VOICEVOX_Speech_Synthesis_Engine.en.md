# Integration with VOICEVOX Speech Synthesis Engine

Here's a brief note introducing our development policies.

- Even as versions increase, we plan to maintain the ability to perform speech synthesis by directly POSTing the values returned from `/audio_query` to `/synthesis`
  - While `AudioQuery` parameters will increase, we'll ensure that default values generate similar output to previous versions
  - We'll maintain backward compatibility by allowing older versions of `AudioQuery` to be POSTed directly to `/synthesis` in newer versions
- Voice styles have been implemented since version 0.7. Style information can be obtained from `/speakers` and `/singers`
  - Speech synthesis can be performed as before by specifying the `style_id` from the style information in the `speaker` parameter
    - The parameter name remains `speaker` for compatibility reasons
