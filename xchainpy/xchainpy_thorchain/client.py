import asyncio

from typing import Optional
from datetime import datetime
import time

from xchainpy.xchainpy_client import interface
from xchainpy.xchainpy_client.models import tx_types
from xchainpy.xchainpy_crypto import crypto as xchainpy_crypto
from xchainpy.xchainpy_util.asset import Asset
from xchainpy_thorchain import utils

from xchainpy.xchainpy_thorchain.cosmos.sdk_client import CosmosSDKClient
import electrumsv_secp256k1


class IThorchainClient():
    def set_client_url(self, client_url):
        pass

    def set_client_url(self):
        pass

    def set_explorer_url(self):
        pass

    def get_explorer_node_url(self):
        pass

    def deposit(self):
        pass


class Client(interface.IXChainClient, IThorchainClient):

    derive_path = "m/44'/118'/0'/0/0"
    phrase = address = network = ''
    private_key = None

    def __init__(self, phrase: str, network: str = "testnet", client_url: str = None, explorer_url: str = None) -> None:
        """Constructor

        Client has to be initialised with network type and phrase.
        It will throw an error if an invalid phrase has been passed.

        :param phrase: phrase of wallet (mnemonic) will be set to the Class
        :param network: network of chain can either be `testnet` or `mainnet`
        :param client_url: client url can be added manually
        :param explorer_url: explorer url can be added manually
        :type phrase: string
        :type network: string
        :type client_url: string
        :type explorer_url: string
        :return: returns void (None)
        :rtype: None
        """
        self.network = network
        self.client_url = client_url or self.get_default_client_url()
        self.explorer_url = explorer_url or self.get_default_explorer_url()
        self.thor_client = self.get_new_thor_client()

        if phrase:
            self.set_phrase(phrase)

    def purge_client(self) -> None:
        """Purge client

        :return: returns void (None)
        :rtype: None
        """
        self.phrase = self.address = ''
        self.private_key = None

    def set_network(self, network: str) -> None:
        """Set/update the current network.

        :param netowrk: network `mainnet` or `testnet`
        :type network: string
        :returns: Nothing (Void/None)
        :raises:
            Exception: "Network must be provided". -> Thrown if network has not been set before.
        """
        if not network:
            raise Exception('Network must be provided')
        else:
            self.network = network
            self.thor_client = self.get_new_thor_client()
            self.address = ''

    def set_phrase(self, phrase: str) -> str:
        if not self.phrase or self.phrase != phrase:
            if not xchainpy_crypto.validate_phrase(phrase):
                raise Exception("invalid phrase")

            self.phrase = phrase
            self.private_key = None
            self.address = ''

        return self.get_address()

    def get_network(self) -> str:
        """Get the current network.

        :returns: The current network. (`mainnet` or `testnet`)
        :rtype: string
        """
        return self.network

    def set_client_url(self, client_url: str) -> None:
        """Set/update the client URL.

        :param client_url: The client url to be set.
        :type client_url: string
        :returns: Nothing (None)
        :rtype: None
        """
        self.client_url = client_url
        self.thor_client = self.get_new_thor_client()

    def get_default_client_url(self) -> object:
        """Get the client url.

        :returns: The client url (both node, rpc) for thorchain based on the network.
        :rtype: {NodeUrl} as a object
        """
        return {
            "testnet": {
                "node": 'https://testnet.thornode.thorchain.info',
                "rpc": 'https://testnet.rpc.thorchain.info',
            },
            "mainnet": {
                "node": 'http://138.68.125.107:1317',
                "rpc": 'http://138.68.125.107:26657',
            },
        }

    def get_default_explorer_url(self) -> str:
        """Get the explorer url.

        :returns: The explorer url (both mainnet and testnet) for thorchain.
        :rtype: string
        """
        return 'https://testnet.thorchain.net' if self.network == 'testnet' else 'https://thorchain.net'

    def get_prefix(self, netowrk: str = None) -> str:
        """Get address prefix based on the network.

        :param network: network
        :type network: string
        :returns: The address prefix based on the network.
        :rtype: string
        """
        if netowrk:
            return 'tthor' if network == 'testnet' else 'thor'
        else:
            return 'tthor' if self.network == 'testnet' else 'thor'

    def get_chain_id(self) -> str:
        """Get the chain id.

        :returns: The chain id based on the network.
        :rtype: string
        """
        return 'thorchain'

    def get_new_thor_client(self):
        """Get new thorchain client.

        :returns: The new thorchain client.
        :rtype: CosmosSDKClient Class    
        """
        network = self.get_network()
        return CosmosSDKClient(server=self.get_default_client_url()[network]["node"], prefix=self.get_prefix(), derive_path="m/44'/931'/0'/0/0", chain_id=self.get_chain_id())

    def get_private_key(self) -> bytes:
        """Get private key.

        :returns: The private key generated from the given phrase
        :rtype: bytes
        :raises: 
            Exception: {"Phrase not set"} -> Throws an error if phrase has not been set before
        """
        if not self.private_key:
            if not self.phrase:
                raise Exception('Phrase not set')

            self.private_key = self.thor_client.seed_to_privkey(self.phrase)

        return self.private_key

    def get_address(self) -> str:
        """Get the current address

        :returns: the current address
        :rtype: string
        :raises: 
            Exception: {"Address has to be set. Or set a phrase by calling `setPhrase` before to use an address of an imported key."}
                        -> Raises if phrase has not been set before. A phrase is needed to create a wallet and to derive an address from it.
        """
        if not self.address:
            self.address = self.thor_client.privkey_to_address(
                self.get_private_key())
            if not self.address:
                raise Exception(
                    "Address has to be set. Or set a phrase by calling `setPhrase` before to use an address of an imported key.")
        return self.address

    async def get_balance(self, address: str = None, asset: str = None) -> list:
        """
         Get the balance of a given address.

         :param address: address By default, it will return the balance of the current wallet. (optional)
         :param asset: asset If not set, it will return all assets available. (optional)
         :returns: The balance of the address.
         :rtype: list
        """
        if not address:
            address = self.get_address()
        response = await self.thor_client.get_balance(address)
        response = response["result"]

        balances = []
        for balance in response:
            if not asset or str(balance['denom']) == str(asset):
                balances.append(
                    {"asset": balance['denom'], "amount": balance['amount']})

        return balances

    async def get_transaction_data(self, tx_id: str) -> object:
        """Get the transaction details of a given transaction id

        if you want to give a hash that is for mainnet and the current self.net is 'testnet',
        you should call self.set_network('mainnet') (and vice versa) and then call this method.

        :param tx_id: The transaction id
        :type tx_id: str
        :returns: The transaction details of the given transaction id
        :rtype: object
        """
        try:
            tx_result = await self.thor_client.txs_hash_get(tx_id)
            if not tx_result:
                raise Exception("transaction not found")
            return tx_result
        except Exception as err:
            raise Exception(err)

    async def transfer(self, amount: int, recipient: str, asset: str = "rune", memo: str = "") -> dict:
        """Transfer balances with MsgSend

        :param amount: amount which you want to send
        :param recipient: the address of recipient to be send
        :param asset: asset need to be send
        :param memo: memo of the transaction
        :type amount: int
        :type recipient: string
        :type asset: string
        :type memo: string
        :returns: The transaction hash
        :rtype: object
        """
        await self.thor_client.make_transaction(self.get_private_key(), self.get_address(), fee_denom=asset, memo=memo)
        self.thor_client.add_transfer(recipient, amount, denom=asset)
        Msg = self.thor_client.get_pushable()
        return await self.thor_client.do_transfer(Msg)

    async def get_fees(self) -> dict:
        """Get the current fees

        :returns: The fees with three rates
        :rtype: dict
        """
        fee = utils.DEFAULT_GAS_VALUE

        return {
            "fast": fee,
            "fastest": fee,
            "average": fee,
        }
