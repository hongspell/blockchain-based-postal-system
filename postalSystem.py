from blockchain import Blockchain

import os

import hashlib
import json
import time
from urllib.parse import urlparse
from uuid import uuid4
from argparse import ArgumentParser
import requests
import sqlite3
import re
from pathlib import Path

from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session, g, Blueprint
from flask_bcrypt import generate_password_hash

from pyzbar.pyzbar import decode
from PIL import Image
import io
import ast

app = Flask(__name__)

node_identifier = str(uuid4()).replace('-', '')

app.secret_key = 'asdffbgsc'  # key


def load_user_data(filename="user.json"):
    default_data = [
        {"username": "admin", "password": "123", "login": 0},
        {"username": "test", "password": "1234", "login": 0}
    ]
    try:
        with open(filename, "r", encoding='utf-8') as file:
            data = json.load(file)
            return data
    except Exception as e:
        print(f"Error loading user data: {e}")
        return default_data


userjsondata = load_user_data('user.json')

# new blockchain object: {"username": (Blockchain() obj)}
# user who first create the blockchain
blockchainlist = []
blockchain = None  # find from blockchainlist with username


##################################################
# blockchain mail
##################################################

@app.route('/mail/<username>/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction will be added to Block {index}'}
    return response


def mine(sender, receiver, content, qrcodeimg=" "):
    last_block = blockchain.last_block
    print(last_block)
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    blockchain.new_transaction(
        sender, receiver, content,
        recipient=node_identifier,
        amount=1, qrcodeimg=qrcodeimg
    )

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return response


def dump_bc(username):
    global blockchain
    with open("blockchain.json", 'w') as f:
        json.dump(blockchain.chain, f, indent=4)


def load_bc(username):
    global blockchain
    fp = Path("blockchain.json")
    if fp.exists():
        with open(fp, 'r') as f:
            blockchain.chain = json.load(f)
    else:
        with open("blockchain.json", 'w') as f:
            json.dump(blockchain.chain, f, indent=4)


def get_content(username):
    content = []
    for block in blockchain.chain:
        if block["index"] == 1:
            continue
        receiver = block['transactions'][0]['receiver']
        sender = block['transactions'][0]['sender']
        if receiver == username:
            content.append([block['transactions'][0]['content'], block['transactions'][0]['qrcodeimg']])
    return content, sender


def verify_block():
    pass


##################################################
# other app
##################################################
# QR code
def image2byte(image):
    img_bytes = io.BytesIO()
    image = image.convert("RGB")
    image.save(img_bytes, format="JPEG")
    image_bytes = img_bytes.getvalue()
    return image_bytes


def byte2image(byte_data):
    image = Image.open(io.BytesIO(byte_data))
    return image


def byte2str(byte_data):
    res = str(byte_data)
    return res


def str2byte(str_data):
    res = ast.literal_eval(str_data)
    return res


##################################################
# base website
# user accounts
##################################################

@app.route('/mail/<username>', methods=['GET', 'POST'], endpoint='mail')
def mail(username):
    print(username)
    global blockchain
    getQRimg = False

    for userinfo in userjsondata:
        if username == userinfo["username"] and userinfo["login"] == 0:
            return redirect("/login")

    # logout
    if request.method == 'POST':
        # print(username,'++',request.form.get('logout'))
        if request.form.get('logout') == 'log out':
            for userinfo in userjsondata:
                if username == userinfo["username"]:
                    print(userinfo)
                    userinfo["login"] = 0
            return redirect("/login")

        # get mail
        elif request.form.get('mail-get') == 'mail-get':
            print("get mail from blockchain")  # TODO: link to bloackchain
            lastcontent = request.form.get('mail-get-textarea')
            content, sender = get_content(username)
            totaln = len(content)
            print(totaln)
            if totaln < 1:
                error = "no content get"
                return render_template("mail.html", error=error, username=username)
            try:
                qr_byte_data = content[-1][1]
                qr_byte_data = str2byte(qr_byte_data)
                image = byte2image(qr_byte_data)
                image.save("static/images/show.png")
                decocdeQR = decode(image)
                mail_containt_get1 = decocdeQR[0].data.decode('ascii')  # test decocdeQR
                getQRimg = True
            except Exception as e:
                print(e)
                mail_containt_get1 = "error qrcode"  # content[-1][0]# debug
            if getQRimg:
                return render_template("mail.html", mail_containt_get0=content[-1][0],
                                       mail_containt_get1=mail_containt_get1, username=username, sender=sender,
                                       getQRimg=getQRimg)
            else:
                return render_template("mail.html", mail_containt_get0=content[-1][0], mail_containt_get1="no qrcode",
                                       username=username, sender=sender)

        # send mail
        elif request.form.get('mail-post') == 'mail-post':
            print("post mail to blockchain")
            mail_containt_post = request.form.get('mail-post-textarea')
            try:
                qrimage = request.files['qrpostfile']
                upload_path = Path(f"static/images/{qrimage.filename}")
                qrimage.save(str(upload_path))
                image = Image.open(upload_path)
                image.save(str(upload_path.parent / "show.png"))
                os.remove(str(upload_path))
                qrcodeimgstr = image2byte(image)
                qrcodeimgstr = byte2str(qrcodeimgstr)
            except Exception as e:
                print(e)
                error = "error qrcode image"
                return render_template("mail.html", error=error, username=username)
            receiver = request.form.get('receiver')

            readytosend = False
            for userinfo in userjsondata:
                if receiver == userinfo["username"]:
                    readytosend = True
                    break
            # print(mail_containt_post) #TODO: link to bloackchain
            if readytosend:
                mine_response = mine(username, receiver, mail_containt_post, qrcodeimg=qrcodeimgstr)  # mine a new block
                time.sleep(0.05)  # debug
                dump_bc(username)
            else:
                error = "user not exist"
                return render_template("mail.html", error=error, username=username)
            # print(mine_response)
            return redirect(f'/mail/{username}')

        # blockchain
        elif request.form.get('new-chain') == 'new-chain':
            if blockchain == None:
                blockchain = Blockchain()
                load_bc(username)
                print("init blockchain")
            else:
                print("existing blockchain")
        elif request.form.get('get-chain') == 'get-chain':
            if blockchain == None:
                return redirect(f'/mail/{username}')
            response = {
                'chain': blockchain.chain,
                'length': len(blockchain.chain),
            }
            response = json.dumps(response, indent=2)
            # print(response)
            return render_template("mail.html", response=response, username=username)

    if blockchain == None:
        error = "Please create a new blockchain!"
        return render_template("mail.html", error=error, username=username)

    return render_template("mail.html", username=username)


@app.route('/', methods=['GET', 'POST'], endpoint='index')
def index():
    username = session.get("username")

    # login
    for userinfo in userjsondata:
        if username == userinfo["username"]:
            if userinfo["login"] == 1:
                userinfo["login"] = 2
                return redirect(f"/mail/{username}")

    return redirect("/login")


@app.route("/logout", endpoint='logout')
def logout():
    session.pop("username", None)

    return redirect("/login")


@app.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # check username if exist
        for userinfo in userjsondata:
            if username == userinfo["username"]:
                error = f'failed, user exist!'
                return render_template('register.html', error=error)
        userjsondata.append({"username": username, "password": password, "login": 0})

        # save userjsondata
        with open("user.json", "w", encoding='utf-8') as f:
            json.dump(userjsondata, f, ensure_ascii=True, indent=4)

        x = f'{username} sign up success!'
        username = None
        return render_template('login.html', x=x, username=username)
    else:
        return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        print("get login post...")
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            for userinfo in userjsondata:
                if username == userinfo["username"] and password == userinfo["password"]:
                    print("sign in success!")
                    session['username'] = username
                    session['password'] = password
                    userinfo["login"] = 1
                    return redirect('/')
            print("login error")
            error = "error user or passworld"
            render_template('login.html', error=error)
        except:
            error = "error user or passworld"
            render_template('login.html', error=error)
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
