

# python virtual envirnment

python3 -m venv .env
 
source .env/bin/activate

# install cdk
pip3 install -r requirements.txt

npm install -g aws-cdk

# bootstrap and deploy
cdk bootstrap

# cdk synth
cdk deploy --all 

