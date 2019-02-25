# Usage

## Configuring two-factor authentication
Since hoover-search has built-in support for TOTP two-factor authentication,
you just need to enable the module by adding a line to `search.env`:

```env
DOCKER_HOOVER_TWOFACTOR_ENABLED=on
```

Then generate an invitation for your user (replace `admin` with your username):

```shell
docker-compose run --rm search ./manage.py invite admin
```

## Importing OCR'ed documents
The OCR process (Optical Character Recognition – extracting machine-readable
text from scanned documents) is done external to Hoover, using e.g. Tesseract.
Try the Python pypdftoocr package. The resulting OCR'ed documents should be PDF
files whose filename is the MD5 checksum of the _original_ document, e.g.
`d41d8cd98f00b204e9800998ecf8427e.pdf`. Put all the OCR'ed files in a folder
(we'll call it _ocr foler_ below) and follow these steps to import them into
Hoover:

* The _ocr folder_ should be in a path accessible to the hoover docker images,
  e.g. in the shared "ocr" folder mapped to the local _ocr_ subfolder,
  `/opt/hoover/collections/ocr/myocr`.

* Register _ocr folder_ as a source for OCR named `myocr` (choose any name you
  like):

```shell
# start workers in a separate, detachable session
docker-compose run --rm snoop--testdata ./manage.py runworkers
# add ocr source
docker-compose run --rm snoop--testdata ./manage.py createocrsource myocr /opt/hoover/snoop/ocr/myocr
# wait for jobs to finish in the workers session
```

## Decrypting PGP emails
If you have access to PGP private keys, snoop can decrypt emails that were
encrypted for those keys. Import the keys into a gnupg home folder placed next
to the `docker-compose.yml` file. Snoop will automatically use this folder when
it encounters an encrypted email.

```shell
gpg --home gnupg --import < path_to_key_file
```

You may need to remove an existing but known password once and use this key instead.

```shell
gpg --home gnupg --export-options export-reset-subkey-passwd --export-secret-subkeys ABCDEF01 > path_to_key_nopassword
gpg --home gnupg --delete-secret-keys ABCDEF01
gpg --home gnupg --delete-key ABCDEF01
gpg --home gnupg --import < path_to_key_nopassword
```

## Profiling
It is possible to generate profiling data using the following commands:
```shell
./createcollection -c <collection_name> -p
./updatesettings -p <collection_names_list>
```

On `createcollection` the `-p` option will add profiling settings for the new
collection. On `updatesettings` the option `-p` will add profiling settings
to the collections in the list. E.g. `-p collection1 collection2`. If the list
was empty it will add profiling settings to all existing collections.

The profiling data can be found in directory `./profiling/<collection_name>`.
One of the following tools can be used to read the profiling data:
- [SnakeViz](https://jiffyclub.github.io/snakeviz/)
- [pyprof2calltree](https://pypi.org/project/pyprof2calltree/)

To remove profiling from a list of collections run the following command:
```shell
./updatesettings -n <collection_names_list>
```

Leave the collection list empty to remove profiling for all collections.
