import pyotp

class TotpAuth:

    def __init__(self, cipher):
        self.cipher = cipher

    def create_secret(self, user) -> str:
        #gera a string do TOTP
        secret = pyotp.random_base32()
        #criptografa e deixa salvo na memoria do usuario
        user.totp_cifrado = self.cipher.encrypt(secret)
        return secret

    def create_uri(self, user) -> str:
        #converte em bytes por conta do formato que o valor vem do banco por conta do tipo da coluna
        secret = self.cipher.decrypt(bytes(user.totp_cifrado))
        #cria um objeto TOTP com o secret criado
        #vincula o usuario e informa o nome do sistema
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name = user.email,
            issuer_name = "ADSUM"
        )

    def verify_code(self, user, code: str) -> bool:
        if not user.totp_cifrado:
            return False
        secret = self.cipher.decrypt(bytes(user.totp_cifrado))
        #verify verifica se o dódigo digitado é válido
        #valid_window=1 é pra deixar uma janela de mais ou menos 30 segundos de validade por código para não dar erro no cadastro por alguma lentidão
        return pyotp.totp.TOTP(secret).verify(code, valid_window=1)