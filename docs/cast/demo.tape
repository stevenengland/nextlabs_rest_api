# Source-of-truth for docs/cast/demo.gif.
# Regenerate with:  vhs docs/cast/demo.tape
#
# This cast uses a small deterministic stub (docs/cast/_fake_nextlabs.sh)
# in place of the real `nextlabs` binary so the output is reproducible
# without a live tenant. See docs/cast/README.md.

Output docs/cast/demo.gif

Set Theme "Catppuccin Mocha"
Set FontSize 16
Set Width 1100
Set Height 520
Set Padding 24
Set TypingSpeed 45ms
Set PlaybackSpeed 1.0

# Set up the deterministic stub on PATH and a friendly prompt.
Hide
Type "alias nextlabs='bash $PWD/docs/cast/_fake_nextlabs.sh'" Enter
Type "export PS1='$ '" Enter
Type "clear" Enter
Show

Sleep 600ms

Type "nextlabs auth login"
Sleep 400ms
Enter
Sleep 1500ms

Type "nextlabs policies search --status APPROVED"
Sleep 400ms
Enter
Sleep 2200ms

Type "nextlabs pdp eval --subject alice --resource doc-42 \"
Sleep 200ms
Enter
Type "                  --resource-type document --action read --application wiki"
Sleep 400ms
Enter
Sleep 2400ms
