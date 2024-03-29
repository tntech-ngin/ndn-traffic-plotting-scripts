# Description
This project is a packet analyser for Named Data Networking (NDN) packets. It uses a MongoDB database to store the packets
and provides various plotting scripts to visualise the data. The included plotting scripts are:
* `components_hexbin.py` - plots the distribution of number of components to its name length
* `grid_throughput.py` - plots the throughput graph of four nodes
* `hoplimit.py` - plots the hop limit of packets
* `lifetime_freshness.py` - plots cdf of lifetime and freshness of packets
* `throughput.py` - plots the throughput graph of a node with number of packets and size of packets in separate plots
* `popular_prefixes.py` - plots the most popular prefixes in interest and data packets
* `content_size_distribution` - plots the distribution of content size of NLSR traffic

# Getting Started
## Prerequisites
* Python >= 3.10
* MongoDB >= 6.0.6
* [ndntdump](https://github.com/usnistgov/ndntdump)

## Installation 
1. Create virtual environment and activate
```bash
cd ndn-packet-view
python3 -m venv venv
source venv/bin/activate
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Create .env
```bash
cp .env.sample .env
```
4. Create ndjson from pcapng.zst dump file
    - Find the local MAC address
    ```bash
    zstdcat <file_path_to_pcapng.zst> | tcpdump -r- -n -e | head -5
    ```
    - Extract into ndjson
    ```bash
    ndntdump -r <file_path_to_pcapng.zst> --local <local_mac_address> -L <path_to_output_file>
    ```
5. Edit `.env` file and change the MONGO_DB_NAME to the name of the database you want to use
6. Index ndjson file into MongoDB
```bash
python -m tools.index <file_path>
```
7. Run the plotting scripts
```bash
python -m tools.plots.<script_name>
```

# Linters and Formatters
The project uses git pre-commit hooks to run linters and formatters. To enable the pre-commit hooks, run the following command:
```bash
pre-commit install
```

## Troubleshooting
If the commit reports conflicts with the unstaged changes, run the pre-commit hooks manually and commit again:
```bash
pre-commit run --all-files
```
or use `--no-verify` flag to skip the pre-commit verification:
```bash
git commit --no-verify -m <message>
```



