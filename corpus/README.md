# Local research reports

Place the supplied research PDFs directly in this directory, keeping their original
`YYYYMMDD_Broker_hash.pdf` filenames. Find Rpt reads reports from this directory.

Only this README is committed. PDFs and other files here are ignored by Git;
do not upload or redistribute the source reports.

For the supplied corpus, restore the metadata-only manifest from the repository root:

```bash
mkdir -p local
cp -n submission/corpus-manifest.json local/split.json
```

Then follow the [main README](../README.md#start-here) to run `/find-rpt`.
