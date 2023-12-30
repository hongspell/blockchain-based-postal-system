import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
from argparse import ArgumentParser
import requests
from flask import Flask, jsonify, request


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.currentTransaction = []
        self.nodes = set()
        self.new_block(proof=100, previous_hash=1)


    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            last_block_hash = self.hash(last_block)

            if block['previous_hash'] != last_block_hash:
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        :return: True if our chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False


    def new_block(self, proof, previous_hash=None):
        # Creates a new Block and adds it to the chain
        """
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """
        # TODO: add postal information
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.currentTransaction,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # Reset the current list of transactions
        self.currentTransaction = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, receiver, content, recipient, amount, qrcodeimg=" ", read=0):
        # Adds a new transaction to the list of transactions
        """
        :param sender: Address of the Sender 
        :param receiver: Address of the receiver
        :param content: Message content
        :return: The index of the Block that will hold this transaction 
        """
        self.currentTransaction.append({
            'sender': sender,
            'receiver': receiver,
            'content': content,
            'qrcodeimg':qrcodeimg,
            'recipient': recipient,
            'amount': amount,
            'read': read
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        :param block: <dict> Block
        :return: <str>
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]


    def proof_of_work(self, lastProof):
        """
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(lastProof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(lastProof, proof):
        """
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """
        guess = f'{lastProof}{proof}'.encode()
        guessHash = hashlib.sha256(guess).hexdigest()
        return guessHash[:4] == '0000'
