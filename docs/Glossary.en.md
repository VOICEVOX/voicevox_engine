# Glossary

This document explains terms used within VOICEVOX ENGINE.  
We plan to add more terms over time. Feel free to send pull requests with additions!

<!--
* Headings should be "### English Name: Code Name (lowercase)"
  * Terms that only appear in code can use just the code name
* Explanations should be 1-3 lines
* Generally avoid line breaks (don't add two spaces at the end)
-->

## Domain Terms

TODO: Compile terms that are presented to users

## Engine-related

TODO

## OpenJTalk-related

### Full Context Label: full-context label

Data obtained from analyzing sentence structure, compiled for each phoneme, or a collection thereof.
Contains information such as which phoneme, which mora position, which accent phrase position, etc.
This is an HTS concept.

### Label: label

Refers to the full context label of a single phoneme.
This is a VOICEVOX-specific definition (within OpenJTalk, "label" refers to the full context label).

### Context: context

Refers to a single element within a full context.
This is a VOICEVOX-specific definition.

### Feature: feature

A label converted into a single-line string.
This is an OpenJTalk concept.
