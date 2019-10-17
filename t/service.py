#! /usr/bin/env python3

# standard libraries
from typing import List, Optional, Union
import argparse
import helper
import json
import math
import os
import platform
import shlex
import string
import subprocess
import threading
import time
import typing

# third-party libraries
import requests

# user-defined modules
from logger import LogLevel, Logger, WriterConfig, ScreenWriter, FileWriter
from connection import Connection
import color
import thread


PROGRAM = "eosio-launcher-service"
PRODUCER_KEY = "EOS6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV"
PREACTIVATE_FEATURE = "0ec7e080177b2c02b278d5088611686b49d739925a92d9bfcacd7fc6b74053bd"

DEFAULT_ADDRESS = "127.0.0.1"
DEFAULT_PORT = 1234
DEFAULT_WDIR = "../build"
DEFAULT_FILE = os.path.join(".", "programs", PROGRAM, PROGRAM)
DEFAULT_START = False
DEFAULT_KILL = False

DEFAULT_CONTRACTS_DIR = "../../eosio.contracts/build/contracts"
DEFAULT_TOTAL_SUPPLY = 1e9
DEFAULT_CLUSTER_ID = 0
DEFAULT_CENTER_NODE_ID = None
DEFAULT_TOPOLOGY = "mesh"
DEFAULT_TOTAL_NODES = 4
DEFAULT_TOTAL_PRODUCERS = 4
DEFAULT_PRODUCER_NODES = 4
DEFAULT_UNSTARTED_NODES = 0
DEFAULT_DONT_VOTE = False
DEFAULT_DONT_BOOTSTRAP = False
DEFAULT_EXTRA_CONFIGS = []

DEFAULT_BUFFERED = True
DEFAULT_MONOCHROME = False

HELP_HELP = "Show this message and exit"
HELP_ADDRESS = "Address of launcher service"
HELP_PORT = "Listening port of launcher service"
HELP_WDIR = "Working directory"
HELP_FILE = "Path to local launcher service file"
HELP_START = "Always start a new launcher service"
HELP_KILL = "Kill existing launcher services (if any)"

HELP_CONTRACTS_DIR = "Directory of eosio smart contracts"
HELP_TOTAL_SUPPLY = "Total supply of tokens"
HELP_CLUSTER_ID = "Cluster ID to launch with"
HELP_CENTER_NODE_ID = "Center node ID for star or bridge"
HELP_TOPOLOGY = "Cluster topology to launch with"
HELP_TOTAL_NODES = "Number of total nodes"
HELP_TOTAL_PRODUCERS = "Number of total producers"
HELP_PRODUCER_NODES = "Number of nodes that have producers"
HELP_UNSTARTED_NODES = "Number of unstarted nodes"
HELP_DONT_VOTE = "Do not vote for producers in bootstrap"
HELP_DONT_BOOTSTRAP = "Launch cluster without bootstrap"

HELP_LOG_LEVEL = "Stdout logging level (numeric)"
HELP_MONOCHROME = "Print in black and white instead of colors"
HELP_UNBUFFER = "Do not buffer for stdout logging"
HELP_EXTRA_CONFIGS = "Extra configs to pass to launcher service"

HELP_LOG_ALL = "Set stdout logging level to ALL (0)"
HELP_TRACE = "Set stdout logging level to TRACE (10)"
HELP_DEBUG = "Set stdout logging level to DEBUG (20)"
HELP_INFO = "Set stdout logging level to INFO (30)"
HELP_WARN = "Set stdout logging level to WARN (40)"
HELP_ERROR = "Set stdout logging level to ERROR (50)"
HELP_FATAL = "Set stdout logging level to FATAL (60)"
HELP_LOG_OFF = "Set stdout logging level to OFF (100)"


class CommandLineArguments:
    def __init__(self):
        cla = self.parse()
        self.address = cla.address
        self.port = cla.port
        self.wdir = cla.wdir
        self.file = cla.file
        self.start = cla.start
        self.kill = cla.kill

        self.contracts_dir = cla.contracts_dir
        self.total_supply = cla.total_supply
        self.cluster_id = cla.cluster_id
        self.topology = cla.topology
        self.center_node_id = cla.center_node_id
        self.total_nodes = cla.total_nodes
        self.total_producers = cla.total_producers
        self.producer_nodes = cla.producer_nodes
        self.unstarted_nodes = cla.unstarted_nodes
        self.dont_vote = cla.dont_vote
        self.dont_bootstrap = cla.dont_bootstrap

        self.threshold = cla.threshold
        self.buffered = cla.buffered
        self.monochrome = cla.monochrome


    @staticmethod
    def parse():
        desc = color.decorate("Launcher Service for EOS Testing Framework", style="underline", fcolor="green")
        left = 5
        form = lambda text, value=None: "{} ({})".format(helper.pad(text, left=left, total=50, char=" ", sep=""), value)
        parser = argparse.ArgumentParser(description=desc, add_help=False, formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=50))
        parser.add_argument("-h", "--help", action="help", help=" " * left + HELP_HELP)

        parser.add_argument("-a", "--address", type=str, metavar="IP", help=form(HELP_ADDRESS, DEFAULT_ADDRESS))
        parser.add_argument("-p", "--port", type=int, help=form(HELP_PORT, DEFAULT_PORT))
        parser.add_argument("-w", "--wdir", type=str, metavar="PATH", help=form(HELP_WDIR, DEFAULT_WDIR))
        parser.add_argument("-f", "--file", type=str, metavar="PATH", help=form(HELP_FILE, DEFAULT_FILE))
        parser.add_argument("-s", "--start", action="store_true", default=None, help=form(HELP_START, DEFAULT_START))
        parser.add_argument("-k", "--kill", action="store_true", default=None, help=form(HELP_KILL, DEFAULT_KILL))

        parser.add_argument("-d", "--contracts-dir", metavar="PATH", help=form(HELP_CONTRACTS_DIR, DEFAULT_CONTRACTS_DIR))
        parser.add_argument("-g", "--total-supply", metavar="NUM", help=form(HELP_TOTAL_SUPPLY, "{:g}".format(DEFAULT_TOTAL_SUPPLY)))
        parser.add_argument("-i", "--cluster-id", dest="cluster_id", type=int, metavar="ID", help=form(HELP_CLUSTER_ID, DEFAULT_CLUSTER_ID))
        parser.add_argument("-t", "--topology", type=str, metavar="SHAPE", help=form(HELP_TOPOLOGY, DEFAULT_TOPOLOGY), choices={"mesh", "star", "bridge", "line", "ring", "tree"})
        parser.add_argument("-c", "--center-node-id", type=int, metavar="ID", help=form(HELP_CENTER_NODE_ID, DEFAULT_CENTER_NODE_ID))
        parser.add_argument("-n", "--total-nodes", type=int, metavar="NUM", help=form(HELP_TOTAL_NODES, DEFAULT_TOTAL_NODES))
        parser.add_argument("-y", "--total-producers", type=int, metavar="NUM", help=form(HELP_TOTAL_PRODUCERS, DEFAULT_TOTAL_PRODUCERS))
        parser.add_argument("-z", "--producer-nodes", type=int, metavar="NUM", help=form(HELP_PRODUCER_NODES, DEFAULT_PRODUCER_NODES))
        parser.add_argument("-u", "--unstarted-nodes", type=int, metavar="NUM", help=form(HELP_UNSTARTED_NODES, DEFAULT_UNSTARTED_NODES))
        parser.add_argument("-j", "--dont-vote", action="store_true", default=None, help=form(HELP_DONT_VOTE, DEFAULT_DONT_VOTE))
        parser.add_argument("-q", "--dont-bootstrap", action="store_true", default=None, help=form(HELP_DONT_BOOTSTRAP, DEFAULT_DONT_BOOTSTRAP))

        threshold = parser.add_mutually_exclusive_group()
        threshold.add_argument("-l", "--log-level", dest="threshold", type=int, metavar="LEVEL", action="store", help=form(HELP_LOG_LEVEL))
        threshold.add_argument("--all", dest="threshold", action="store_const", const="ALL", help=form(HELP_LOG_ALL))
        threshold.add_argument("--trace", dest="threshold", action="store_const", const="TRACE", help=form(HELP_TRACE))
        threshold.add_argument("--debug", dest="threshold", action="store_const", const="DEBUG", help=form(HELP_DEBUG))
        threshold.add_argument("--info", dest="threshold", action="store_const", const="INFO", help=form(HELP_INFO))
        threshold.add_argument("--warn", dest="threshold", action="store_const", const="WARN", help=form(HELP_WARN))
        threshold.add_argument("--error", dest="threshold", action="store_const", const="ERROR", help=form(HELP_ERROR))
        threshold.add_argument("--fatal", dest="threshold", action="store_const", const="FATAL", help=form(HELP_FATAL))
        threshold.add_argument("--off", dest="threshold", action="store_const", const="OFF", help=form(HELP_LOG_OFF))
        parser.add_argument("-x", "--unbuffer", dest="buffered", action="store_false", default=True, help=form(HELP_UNBUFFER, not DEFAULT_BUFFERED))
        parser.add_argument("-m", "--monochrome", action="store_true", default=False, help=form(HELP_MONOCHROME, DEFAULT_MONOCHROME))

        return parser.parse_args()


class Service:
    def __init__(self, address=None, port=None, wdir=None, file=None, start=None, kill=None, logger=None, dont_connect=False):
        # read command-line arguments
        self.cla = CommandLineArguments()

        # configure service
        self.address = helper.override(DEFAULT_ADDRESS, address, self.cla.address)
        self.port    = helper.override(DEFAULT_PORT,    port,    self.cla.port)
        self.wdir    = helper.override(DEFAULT_WDIR,    wdir,    self.cla.wdir)
        self.file    = helper.override(DEFAULT_FILE,    file,    self.cla.file)
        self.start   = helper.override(DEFAULT_START,   start,   self.cla.start)
        self.kill    = helper.override(DEFAULT_KILL,    kill,    self.cla.kill)

        # register logger
        self.register_logger(logger)

        # connect
        if not dont_connect:
            self.connect()


    def register_logger(self, logger):
        self.logger = logger
        for w in self.logger.writers:
            if isinstance(w, ScreenWriter):
                th = helper.override(w.threshold, self.cla.threshold)
                if isinstance(th, str):
                    th = LogLevel[th]
                self.threshold = w.threshold = th
                self.buffered = w.buffered = helper.override(DEFAULT_BUFFERED, w.buffered, self.cla.buffered)
                self.monochrome = w.monochrome = helper.override(DEFAULT_MONOCHROME, w.monochrome, self.cla.monochrome)


    def connect(self):
        self.change_working_dir()
        self.empty_log_files()
        self.print_system_info()
        self.print_config()
        if self.address == "127.0.0.1":
            self.connect_to_local_service()
        else:
            self.connect_to_remote_service()


    def empty_log_files(self):
        for w in self.logger.writers:
            if isinstance(w, FileWriter):
                with open(w.filename, "w"):
                    pass


    def print_system_info(self):
        self.print_header("system info")
        self.logger.debug("{:22}{}".format("UTC Time", time.strftime("%Y-%m-%d %H:%M:%S %Z", time.gmtime())))
        self.logger.debug("{:22}{}".format("Local Time", time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime())))
        self.logger.debug("{:22}{}".format("Platform", platform.platform()))


    def print_config(self):
        self.print_header("service configuration")

        # print service config
        self.print_formatted_config("-a: address", HELP_ADDRESS, self.address, DEFAULT_ADDRESS)
        self.print_formatted_config("-p: port",    HELP_PORT,    self.port,    DEFAULT_PORT)
        self.print_formatted_config("-w: wdir",    HELP_WDIR,    self.wdir,    DEFAULT_WDIR)
        self.print_formatted_config("-f: file",    HELP_FILE,    self.file,    DEFAULT_FILE)
        self.print_formatted_config("-s: start",   HELP_START,   self.start,   DEFAULT_START)
        self.print_formatted_config("-k: kill",    HELP_KILL,    self.kill,    DEFAULT_KILL)

        # print logger config (for screen logging)
        try:
            log_level = "{} ({})".format(LogLevel(self.threshold).name, self.threshold)
        except ValueError:
            log_level = self.threshold
        self.print_formatted_config("-l: log-level",  HELP_LOG_LEVEL,  log_level)
        self.print_formatted_config("-x: unbuffer",   HELP_UNBUFFER,   not self.buffered, not DEFAULT_BUFFERED)
        self.print_formatted_config("-m: monochrome", HELP_MONOCHROME, self.monochrome,   DEFAULT_MONOCHROME)


    def change_working_dir(self):
        os.chdir(self.wdir)
        self.print_header("change working directory")
        self.logger.debug("{:22}{}".format("Working Directory", os.getcwd()))


    def connect_to_local_service(self):
        self.print_header("connect to local service")
        pid_list = self.get_local_services()
        if self.kill:
            self.kill_local_services(pid_list)
            pid_list.clear()
        if pid_list and not self.start:
            self.connect_to_existing_local_service(pid_list[0])
        else:
            self.start_local_service()


    # TO DO IN FUTURE
    def connect_to_remote_service(self):
        self.print_header("connect to remote service")
        self.logger.warn("WARNING: Local service file setting (file={}) ignored.".format(helper.compress(self.file)))
        self.logger.warn("WARNING: Setting to always start a local service (start={}) ignored.".format(self.start))
        self.logger.warn("WARNING: Setting to kill local services (kill={}) ignored.".format(self.kill))
        self.logger.fatal("FATAL: Connecting to a remote service is experimental at this moment.")


    def print_header(self, text, level="DEBUG", buffer=False):
        self.logger.log(helper.format_header(text, level=str(level)), level=level, buffer=buffer)


    def print_formatted_config(self, label, help, value, default_value=None, compress=True):
        to_mark = value != default_value
        compressed = helper.compress(str(value))
        highlighted = color.blue(compressed) if to_mark else compressed
        self.logger.debug("{:31}{:48}{}".format(color.yellow(label), help, highlighted))


    def get_local_services(self) -> typing.List[int]:
        """Returns a list of 0, 1, or more process IDs"""
        pid_list = helper.get_pid_list_by_pattern(PROGRAM)
        if len(pid_list) == 0:
            self.logger.debug(color.yellow("No launcher is running currently."))
        elif len(pid_list) == 1:
            self.logger.debug(color.green("Launcher service is running with process ID [{}].".format(pid_list[0])))
        else:
            self.logger.debug(color.green("Multiple launcher services are running with process IDs {}".format(pid_list)))
        return pid_list


    def kill_local_services(self, pid_list):
        for x in pid_list:
            self.logger.debug(color.yellow("Killing exisiting launcher service with process ID [{}].".format(x)))
            helper.terminate(x)


    def connect_to_existing_local_service(self, pid):
        cmd_and_args = helper.get_cmd_and_args_by_pid(pid)
        for ind, val in enumerate(shlex.split(cmd_and_args)):
            if ind == 0:
                existing_file = val
            elif val.startswith("--http-server-address"):
                existing_port = int(val.split(":")[-1])
                break
        else:
            self.logger.error("ERROR: Failed to extract \"--http-server-address\" from \"{}\" (process ID {})!".format(cmd_and_args, pid), assert_false=True)
        self.logger.debug(color.green("Connecting to existing launcher service with process ID [{}].".format(pid)))
        self.logger.debug(color.green("No new launcher service will be started."))
        self.logger.debug("Configuration of existing launcher service:")
        self.logger.debug("--- Listening port: [{}]".format(color.blue(existing_port)))
        self.logger.debug("--- Path to file: [{}]".format(color.blue(existing_file)))
        if self.port != existing_port:
            self.logger.warn("WARNING: Port setting (port={}) ignored.".format(self.port))
            self.port = existing_port
        if self.file != existing_file:
            self.logger.warn("WARNING: File setting (file={}) ignored.".format(self.file))
            self.file = existing_file
        self.logger.debug("To always start a new launcher service, pass {} or {}.".format(color.yellow("-s"), color.yellow("--start")))
        self.logger.debug("To kill existing launcher services, pass {} or {}.".format(color.yellow("-k"), color.yellow("--kill")))


    def start_local_service(self):
        self.logger.debug(color.green("Starting a new launcher service."))
        helper.quiet_run([self.file, "--http-server-address=0.0.0.0:{}".format(self.port), "--http-threads=4"])
        if not self.get_local_services():
            self.logger.error("ERROR: Launcher service is not started properly!", assert_false=True)


class Cluster:
    def __init__(self, service, contracts_dir=None, total_supply=None, cluster_id=None, topology=None, center_node_id=None, total_nodes=None, total_producers=None, producer_nodes=None, unstarted_nodes=None, extra_configs: typing.List[str] = None, dont_vote=None, dont_bootstrap=None):
        # register service
        self.service = service
        self.cla = service.cla
        self.logger = service.logger
        self.print_header = service.print_header
        self.print_formatted_config= service.print_formatted_config

        # configure cluster
        self.contracts_dir   = helper.override(DEFAULT_CONTRACTS_DIR,   contracts_dir,   self.cla.contracts_dir)
        self.total_supply    = helper.override(DEFAULT_TOTAL_SUPPLY,    total_supply,    self.cla.total_supply)
        self.cluster_id      = helper.override(DEFAULT_CLUSTER_ID,      cluster_id,      self.cla.cluster_id)
        self.topology        = helper.override(DEFAULT_TOPOLOGY,        topology,        self.cla.topology)
        self.center_node_id  = helper.override(DEFAULT_CENTER_NODE_ID,  center_node_id,  self.cla.center_node_id)
        self.total_nodes     = helper.override(DEFAULT_TOTAL_NODES,     total_nodes,     self.cla.total_nodes)
        self.total_producers = helper.override(DEFAULT_TOTAL_PRODUCERS, total_producers, self.cla.total_producers)
        self.producer_nodes  = helper.override(DEFAULT_PRODUCER_NODES,  producer_nodes,  self.cla.producer_nodes)
        self.unstarted_nodes = helper.override(DEFAULT_UNSTARTED_NODES, unstarted_nodes, self.cla.unstarted_nodes)
        self.dont_vote       = helper.override(DEFAULT_DONT_VOTE,       dont_vote,       self.cla.dont_vote)
        self.dont_bootstrap  = helper.override(DEFAULT_DONT_BOOTSTRAP,  dont_bootstrap,  self.cla.dont_bootstrap)
        self.extra_configs   = helper.override(DEFAULT_EXTRA_CONFIGS,   extra_configs)

        # check for logical errors in config
        self.check_config()

        # Example
        # -------
        # Given 4 nodes, 3 (non-eosio) producers and 2 producer nodes, the mappings would be:
        # self.nodes = [{"node_id": 0, "producers": "eosio", "defproducera", "defproducerb"},
        #               {"node_id": 1, "producers": "defproducerc"},
        #               {"node_id": 2, "producers": ""},
        #               {"node_id": 3, "producers": ""}]
        # self.producers = {"defproducera": 0, "defproducerb": 1, "defproducerc": 2}

        # establish mappings between nodes and producers
        self.nodes = []
        self.producers = {}
        q, r = divmod(self.total_producers, self.producer_nodes)
        for i in range(self.total_nodes):
            self.nodes += [{"node_id": i}]
            if i < self.producer_nodes:
                prod = [] if i else ["eosio"]
                for j in range(i * q + r if i else 0, (i + 1) * q + r):
                    name = self.get_defproducer_names(j)
                    prod.append(name)
                    self.producers[name] = i
                self.nodes[i]["producers"] = prod

        # launch cluster
        if self.dont_bootstrap:
            self.launch_without_bootstrap()
        else:
            self.bootstrap(dont_vote=self.dont_vote)


    def check_config(self):
        assert self.cluster_id >= 0, "cluster_id ({}) < 0.".format(self.cluster_id)
        assert self.total_nodes >= self.producer_nodes + self.unstarted_nodes, "total_node ({}) < producer_nodes ({}) + unstarted_nodes ({}).".format(self.total_nodes, self.producer_nodes, self.unstarted_nodes)
        if self.topology in ("star", "bridge"):
            assert self.center_node_id is not None, "center_node_id is not specified when topology is \"{}\".".format(self.topology)
        if self.topology == "bridge":
            assert self.center_node_id not in (0, self.total_nodes-1), "center_node_id ({}) cannot be 0 or last node ({}) when topology is \"bridge\".".format(self.center_node_id, self.total_nodes-1)


    def launch_without_bootstrap(self):
        self.print_header("Launch (without bootstrap) starts.", level="INFO")
        self.print_config()
        self.launch_cluster()
        self.get_cluster_info()
        self.set_bios_contract()
        self.print_header("Launch (without bootstrap) ends.", level="INFO")


    # TODO: ADD isInSync() after launch cluster
    def bootstrap(self, dont_vote=False):
        """
        Bootstrap
        ---------
        1. launch a cluster
        2. get cluster info
        3. create bios account
        4. schedule protocol feature activations
        5. set eosio.token contract
        6. create tokens
        7. issue tokens
        8. set system contract
        9. init system contract
        10. create producer accounts
        11. register producers
        12. vote for producers
        13. verify head producer
        """
        # self.logger.info(color.bold(">>> Bootstrap{} starts.").format(" (without voting)" if dont_vote else ""))
        self.print_header("Bootstrap{} starts.".format(" (without voting)" if dont_vote else ""), level="INFO")
        self.print_config()
        self.launch_cluster()
        self.get_cluster_info()
        self.create_bios_accounts()
        self.schedule_protocol_feature_activations()
        self.set_token_contract()
        self.create_tokens(maximum_supply=self.total_supply)
        self.issue_tokens(quantity=self.total_supply)
        self.set_system_contract()
        self.init_system_contract()
        self.create_and_register_producers_in_parallel()
        if not dont_vote:
            self.vote_for_producers(voter="defproducera", voted_producers=list(self.producers.keys())[:min(21, len(self.producers))])
            self.verify_head_block_producer()
        self.print_header("Bootstrap{} ends.".format(" (without voting)" if dont_vote else ""), level="INFO")


    def print_config(self):
        self.print_header("cluster configuration")
        self.print_formatted_config("-d: contracts_dir",   HELP_CONTRACTS_DIR,     self.contracts_dir,   DEFAULT_CONTRACTS_DIR)
        self.print_formatted_config("-i: cluster_id",      HELP_CLUSTER_ID,        self.cluster_id,      DEFAULT_CLUSTER_ID)
        self.print_formatted_config("-t: topology",        HELP_TOPOLOGY,          self.topology,        DEFAULT_TOPOLOGY)
        self.print_formatted_config("-c: center_node_id",  HELP_CENTER_NODE_ID,    self.center_node_id,  DEFAULT_CENTER_NODE_ID)
        self.print_formatted_config("-n: total_nodes",     HELP_TOTAL_NODES,       self.total_nodes,     DEFAULT_TOTAL_NODES)
        self.print_formatted_config("-y: total_producers", HELP_TOTAL_PRODUCERS,   self.total_producers, DEFAULT_TOTAL_PRODUCERS)
        self.print_formatted_config("-z: producer_nodes",  HELP_PRODUCER_NODES,    self.producer_nodes,  DEFAULT_PRODUCER_NODES)
        self.print_formatted_config("-u: unstarted_nodes", HELP_UNSTARTED_NODES,   self.unstarted_nodes, DEFAULT_UNSTARTED_NODES)
        self.print_formatted_config("-j: dont_vote",       HELP_DONT_VOTE,         self.dont_vote,       DEFAULT_DONT_VOTE)
        self.print_formatted_config("-q: dont_bootstrap",  HELP_DONT_BOOTSTRAP,    self.dont_bootstrap,  DEFAULT_DONT_BOOTSTRAP)
        self.print_formatted_config("... extra_configs",   HELP_EXTRA_CONFIGS,     self.extra_configs,   DEFAULT_EXTRA_CONFIGS)


    def launch_cluster(self):
        return self.call("launch_cluster",
                         nodes=self.nodes,
                         node_count=self.total_nodes,
                         shape=self.topology,
                         center_node_id=self.center_node_id,
                         extra_configs=self.extra_configs)


    def get_cluster_info(self, node_id=0, level="DEBUG", buffer=False):
        return self.call("get_cluster_info",
                         node_id=node_id,
                         level=level,
                         buffer=buffer)


    def set_bios_contract(self):
        contract = "eosio.bios"
        return self.set_contract(account="eosio",
                                 contract_file=self.get_wasm_file(contract),
                                 abi_file=self.get_abi_file(contract),
                                 name=contract)


    def create_bios_accounts(self, verify_key="irreversible"):
        accounts = [{"name":"eosio.bpay"},
                    {"name":"eosio.msig"},
                    {"name":"eosio.names"},
                    {"name":"eosio.ram"},
                    {"name":"eosio.ramfee"},
                    {"name":"eosio.rex"},
                    {"name":"eosio.saving"},
                    {"name":"eosio.stake"},
                    {"name":"eosio.token"},
                    {"name":"eosio.upay"}]
        return self.call("create_bios_accounts",
                         creator="eosio",
                         accounts=accounts,
                         verify_key=verify_key)


    def schedule_protocol_feature_activations(self):
        return self.call("schedule_protocol_feature_activations",
                         protocol_features_to_activate=[PREACTIVATE_FEATURE])


    def set_token_contract(self):
        contract = "eosio.token"
        return self.set_contract(account=contract,
                                 contract_file=self.get_wasm_file(contract),
                                 abi_file=self.get_abi_file(contract),
                                 name=contract)


    def create_tokens(self, maximum_supply):
        formatted = helper.format_tokens(maximum_supply)
        actions = [{"account": "eosio.token",
                    "action": "create",
                    "permissions": [{"actor": "eosio.token",
                                     "permission": "active"}],
                    "data": {"issuer": "eosio",
                             "maximum_supply": formatted,
                             "can_freeze": 0,
                             "can_recall": 0,
                             "can_whitelist":0}}]
        return self.push_actions(actions=actions, name="create tokens")


    def issue_tokens(self, quantity):
        formatted = helper.format_tokens(quantity)
        actions = [{"account": "eosio.token",
                    "action": "issue",
                    "permissions": [{"actor": "eosio",
                                    "permission": "active"}],
                    "data": {"to": "eosio",
                             "quantity": formatted,
                             "memo": "hi"}}]
        return self.push_actions(actions=actions, name="issue tokens")


    def set_system_contract(self):
        contract = "eosio.system"
        self.set_contract(contract_file=self.get_wasm_file(contract),
                          abi_file=self.get_abi_file(contract),
                          account="eosio",
                          name=contract)


    def init_system_contract(self):
        actions = [{"account": "eosio",
                    "action": "init",
                    "permissions": [{"actor": "eosio",
                                     "permission": "active"}],
                    "data": {"version": 0,
                             "core": "4,SYS"}}]
        return self.push_actions(actions=actions, name="init system contract")


    def create_and_register_producers_in_parallel(self):
        amount = self.total_supply * 0.075
        threads = []
        channel = {}
        def report(channel, thread_id, message):
            channel[thread_id] = message
        for p in self.producers:
            def create_and_register_producers(amount):
                # CAUTION
                # -------
                # Must keep p's value in a local variable (producer),
                # since p may change in multithreading
                producer = p
                formatted = helper.format_tokens(amount)
                self.create_account(creator="eosio",
                                    name=producer,
                                    stake_cpu=formatted,
                                    stake_net=formatted,
                                    buy_ram_bytes=1048576,
                                    transfer=True,
                                    buffer=True)
                self.register_producer(producer=producer, buffer=True)
            t = thread.ExceptionThread(channel, report, target=create_and_register_producers, args=(amount,))
            amount = max(amount / 2, 100)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        if len(channel) != 0:
            self.logger.error("{} exception(s) occurred in creating and registering producers.".format(len(channel)))
            count = 0
            for thread_id in channel:
                self.logger.error(channel[thread_id])
                count += 1
                if count == 5:
                    break


    def vote_for_producers(self, voter, voted_producers: List[str],  buffer=False):
        assert len(voted_producers) <= 30, "An account cannot votes for more than 30 producers. {} voted for {} producers.".format(voter, len(voted_producers))
        actions = [{"account": "eosio",
                    "action": "voteproducer",
                    "permissions": [{"actor": "{}".format(voter),
                                     "permission": "active"}],
                    "data": {"voter": "{}".format(voter),
                             "proxy": "",
                             "producers": voted_producers}}]
        return self.push_actions(actions=actions, name="votes for producers", buffer=buffer)


    # TO REVIEW
    def verify_head_block_producer(self, retry=10, sleep=1):
        self.print_header("get head block producer")
        conn = self.get_cluster_info(level="TRACE")
        extract_head_block_producer = lambda conn: json.loads(conn.response.text)["result"][0][1]["head_block_producer"]
        while retry >= 0:
            conn = self.get_cluster_info(level="TRACE")
            head_block_producer = extract_head_block_producer(conn)
            if head_block_producer == "eosio":
                self.logger.debug(color.yellow("Head block producer is still \"eosio\"."))
            else:
                self.logger.debug(color.green("Head block producer is now \"{}\", no longer eosio.".format(head_block_producer)))
                break
            self.logger.trace("{} {} for head block producer verification...".format(retry, "retries remain" if retry > 1 else "retry remains"))
            self.logger.trace("Sleep for {}s before next retry...".format(sleep))
            time.sleep(sleep)
            retry -= 1
        assert head_block_producer != "eosio", "Head block producer is still \"eosio\"."


    def create_account(self, creator, name, stake_cpu, stake_net, buy_ram_bytes, transfer, node_id=0, verify_key="irreversible", buffer=False):
        return self.call("create_account",
                         creator=creator,
                         name=name,
                         stake_cpu=stake_cpu,
                         stake_net=stake_net,
                         buy_ram_bytes=buy_ram_bytes,
                         transfer=transfer,
                         node_id=node_id,
                         verify_key=verify_key,
                         header="create \"{}\" account".format(name),
                         buffer=buffer)


    def register_producer(self, producer, buffer=False):
        actions = [{"account": "eosio",
                    "action": "regproducer",
                    "permissions": [{"actor": "{}".format(producer),
                                    "permission": "active"}],
                    "data": {"producer": "{}".format(producer),
                             "producer_key": PRODUCER_KEY,
                             "url": "www.test.com",
                             "location": 0}}]
        return self.push_actions(actions=actions, name="register \"{}\" producer".format(producer), buffer=buffer)



    def set_contract(self, account, contract_file, abi_file, node_id=0, verify_key="irreversible", name=None, buffer=False):
        return self.call("set_contract",
                         account=account,
                         contract_file=contract_file,
                         abi_file=abi_file,
                         node_id=node_id,
                         verify_key=verify_key,
                         header="set <{}> contract".format(name) if name else None,
                         buffer=buffer)


    def push_actions(self, actions, node_id=0, verify_key="irreversible", name=None, buffer=False):
        return self.call("push_actions",
                         actions=actions,
                         node_id=node_id,
                         verify_key=verify_key,
                         header=name,
                         buffer=buffer)


    # TODO: set retry from command-line
    def call(self,
             func: str,
             retry=40,
             sleep=0.25,
             verify_key=None,
             header=None,
             level="DEBUG",
             buffer=False,
             dont_flush=False,
             **data) -> Connection:
        """
        call
        ----
        1. print header
        2. establish connection
        3. log url and request of connection
        4. retry connection if response not ok
        5. log response
        6. verify transaction
        """
        data.setdefault("cluster_id", self.cluster_id)
        data.setdefault("node_id", 0)
        header = header if header else func.replace("_", " ")
        self.print_header(header, level=level, buffer=buffer)
        conn = Connection(url="http://{}:{}/v1/launcher/{}".format(self.service.address, self.service.port, func), data=data)
        try:
            self.logger.log(conn.url, level=level, buffer=buffer)
            self.logger.log(conn.request_text, level=level, buffer=buffer)
            while not conn.ok and retry > 0:
                self.logger.trace(conn.response_code, buffer=buffer)
                self.logger.trace("{} {} for http connection...".format(retry, "retries remain" if retry > 1 else "retry remains"), buffer=buffer)
                self.logger.trace("Sleep for {}s before next retry...".format(sleep), buffer=buffer)
                time.sleep(sleep)
                conn.attempt()
                retry -= 1
            if conn.response.ok:
                self.logger.log(conn.response_code, level=level, buffer=buffer)
                if conn.transaction_id:
                    self.logger.log(color.green("<Transaction ID> {}".format(conn.transaction_id)), level=level, buffer=buffer)
                else:
                    self.logger.log(color.yellow("<No Transaction ID>"), level=level, buffer=buffer)
                self.logger.trace(conn.response_text, buffer=buffer)
            else:
                self.logger.error(conn.response_code)
                self.logger.error(conn.response_text)
            if verify_key:
                assert self.verify(transaction_id=conn.transaction_id, verify_key=verify_key, level=level, buffer=buffer)
            elif conn.transaction_id:
                self.logger.warn("WARNING: Verification of transaction ID {} skipped.".format(conn.transaction_id), level=level, buffer=buffer)
            if buffer and not dont_flush:
                self.logger.flush()
        except AssertionError:
            self.logger.flush()
        return conn


    def verify(self, transaction_id, verify_key="irreversible", retry=40, sleep=0.25, level="DEBUG", buffer=False):
        while retry >= 0:
            if self.verify_transaction(transaction_id=transaction_id, verify_key=verify_key, buffer=buffer):
                self.logger.log("{}".format(color.black_on_green(verify_key.title())), level=level, buffer=buffer)
                return True
            time.sleep(sleep)
            retry -= 1
        self.logger.error(color.decorate("{}".format(verify_key.title()), fcolor="black", bcolor="green"))
        return False


    def verify_transaction(self, transaction_id, verify_key="irreversible", level="TRACE", buffer=False):
        conn = self.call("verify_transaction", transaction_id=transaction_id, verify_key=None, level=level, buffer=buffer, dont_flush=True)
        return helper.extract(conn.response, key=verify_key, fallback=False)


    # Note: not called in this script
    def stop_node(self):
        return self.call("stop_node")


    # Note: not called in this script
    def start_node(self):
        return self.call("start_node")


    # Note: not called in this script
    def get_block(self, block_num_or_id):
        return self.call("get_block", block_num_or_id=block_num_or_id)


    def get_wasm_file(self, contract):
        return os.path.join(self.contracts_dir, contract, contract + ".wasm")


    def get_abi_file(self, contract):
        return os.path.join(self.contracts_dir, contract, contract + ".abi")


    @staticmethod
    def get_defproducer_names(num):

        def base26_to_int(s: str):
            res = 0
            for c in s:
                res *= 26
                res += ord(c) - ord('a')
            return res

        def int_to_base26(x: int):
            res = ""
            while True:
                q, r = divmod(x, 26)
                res = chr(ord('a') + r) + res
                x = q
                if q == 0:
                    break
            return res

        # 8031810176 = 26 ** 7 is integer for "baaaaaaa" in base26
        return "defproducer" + string.ascii_lowercase[num] if num < 26 else "defpr" + int_to_base26(8031810176 + num)[1:]


def test():
    debug_buffer_colo = WriterConfig(threshold="DEBUG", buffered=True,  monochrome=False)
    trace_buffer_colo = WriterConfig(threshold="TRACE", buffered=True,  monochrome=False)
    trace_unbuff_mono = WriterConfig(threshold="TRACE", buffered=False, monochrome=True)

    logger = Logger(ScreenWriter(config=debug_buffer_colo),
                    FileWriter(config=debug_buffer_colo, filename="debug_buffer_colo.log"),
                    FileWriter(config=trace_buffer_colo, filename="trace_buffer_colo.log"),
                    FileWriter(config=trace_unbuff_mono, filename="trace_unbuff_mono.log"))
    service = Service(logger=logger)
    cluster = Cluster(service=service)


# TODO:
# 2. isInSync
# 5. trace -- verify txn show response: better Connection level show
if __name__ == "__main__":
    test()