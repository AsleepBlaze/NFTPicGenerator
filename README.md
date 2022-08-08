# NFTPicGenerator
This project is used to generate pictures using PSD files of a specific format.

## About PSD
The PSD should have many layer groups and all the layers in a layer group are the same part of the picture. The script will randomly select a layer from each layer group and then generate a picture with all the selected layers.

## Installation
1. Copy config.py.sample to the peer directory, named `config.py`.
2. Run `pip install -r requirements.txt` (python3 is required).

## Usage
1. Copy your PSD file into `data/assemble/psd` directory (create the directory if not exist).
2. Run `python console.py psd:assemble sample`, replace the `sample` with your PSD file name (no ext is required).

### You can generate thumbnails
Run `python console.py psd:assemble sample -s 500,500`

This command will generate pictures of size 500x500.

### You can generate many pictures
Run `python console.py psd:assemble sample -l 10`

This command will generate 10 pictures.

Note: <font color=red>The value of `-l` must not greater than the maximum number that the PSD can generate (calculated by script)</font>

### You can generate JPG pictures, defalut is PNG.
Run `python console.py psd:assemble sample --use_jpg`