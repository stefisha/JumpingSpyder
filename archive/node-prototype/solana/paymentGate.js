const { Connection, Keypair, PublicKey } = require('@solana/web3.js');
const bip39 = require('bip39');
const { HDKey } = require('micro-ed25519-hdkey');
 
const mnemonic = process.env.MNEMONIC;
 
// arguments: (mnemonic, password)
const seed = bip39.mnemonicToSeedSync(mnemonic, '');
const hd = HDKey.fromMasterSeed(seed.toString('hex'));
 
function getPublicKeyForUserId(userId){
  const child = hd.derive(`m/44'/501'/${userId}'/0'`);
  const keypair = Keypair.fromSeed(child.privateKey);
  return keypair.publicKey.toBase58();
}
 
async function checkBalance(publicKey) {
  const connection = new Connection('https://api.mainnet-beta.solana.com/');
  const balance = await connection.getBalance(new PublicKey(publicKey));
  return balance / 1e9; // Convert lamports to SOL
}

module.exports = {
  getPublicKeyForUserId,
  checkBalance
};