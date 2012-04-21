#! /usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import html
import requests


class CreditAgricoleParser():
    "Récupère des informations concernant un compte Credit Agricole"
    
    AUTH_FORM_TARGET = 'https://www.cr867-comete-g2-enligne.credit-agricole.fr/stb/entreeBam'

    def __init__(self):
        self.session = requests.session(verify=True)

    def get_login_page(self):
        """Renvoie le code source HTML de la page contenant le formulaire d'authentification."""
        data= {
            'origine': 'vitrine',
            'situationTravail': 'BANQUAIRE',
            'canal': 'WEB',
        }
        return self.session.post(self.AUTH_FORM_TARGET, data=data).content
    
    
    def get_trans_dict(self, login_page_source):
        """La page d'authentification utilise une grille 5x5 dans laquelle les chiffres 0-9 sont placés aléatoirement.
        Quand on clique sur un des chiffres, le systeme enregistre la position du clic dans la grille.
        Les cases sont numérotées ainsi:
        1  2  3  4  5
        6  7  8  9  10
        11 12 13 14 15
        16 17 18 19 20
        21 22 23 24 25
        
        Cette méthode renvoie un dictionnaire dont les clés sont les chiffres de 1 a 9 et les valeurs leur traduction en termes de position dans la grille.
        """
        tree = html.fromstring(login_page_source)
        nodes = tree.xpath("//table[@id='pave-saisie-code']//td[@onclick]")
        return dict((node.text_content().strip(), node.get('onclick')[14:16]) for node in nodes)


    def get_post_data_for_login(self, login_page_source, account_number, password):
        """Cette méthode se charge de renvoyer un dictionanire correspondant aux champs qui doivent etre envoyés pour que l'authentification soit positive.
        Il faut en particulier "traduire" le mot de passe a 6 chiffres (cf la méthode get_trans_dict)."""
        tree = html.fromstring(login_page_source)
        nodes = tree.xpath("//form[@name='formulaire']//input")
        data = dict((node.get('name'), node.get('value')) for node in nodes)
        
        trans_dict = self.get_trans_dict(login_page_source)
        
        data.update({
            'CCCRYC2': '000000',
            'CCPTE': account_number,
            'CCCRYC': ','.join(trans_dict.get(e) for e in password)
        })

        return data

    def get_landing_page(self, login_post_data):
        """Retourne le code source de la page d'accueil une fois l'utilisateur authentifié."""
        return self.session.post(self.AUTH_FORM_TARGET, data=login_post_data).content
    

    def get_balance(self, landing_page_source):
        """Renvoie une liste de tous les comptes avec pour chacun le nom du compte, son numéro ainsi que le solde."""
        tree = html.fromstring(landing_page_source)
        rows = tree.xpath("//table[@class='ca-table']/tr[@class!='tr-thead']")

        def format_data(row):
            return {
                'name': row.xpath('./td[1]')[0].text_content().strip(),
                'number': row.xpath('./td[3]')[0].text_content().strip(),
                'balance': row.xpath('./td[4]')[0].text_content().strip(),
            }
        return [format_data(row) for row in rows]
    
    
    def connect(self, username, password):
        """Cette méthode se charge de se conencter au site et renvoie la code source de la page d'accueil une fois l'utilisateur connecté."""
        login_page = self.get_login_page()
        d = self.get_post_data_for_login(login_page, username, password)
        landing_page = self.get_landing_page(d)
        
        return landing_page
    
    
    def connect_and_get_balance(self, username, password):
        """Cette méthode se connecte au site en renvoie une lsite de tous les comptes associés."""
        
        return self.get_balance(self.connect(username, password))
        


#exemple basique d'utilisation:
if __name__ == '__main__':
    from optparse import OptionParser
    from getpass import getpass
    p = OptionParser()
    p.add_option('-u', '--username', help=u"Le numéro du compte utilisé pour se connecter", dest='username')
    p.add_option('-p', '--password', help=u"Le mot de passe à 6 chiffres", dest='password')
    options, args = p.parse_args()
    
    username = options.username or raw_input('Numéro de compte :')
    password = options.password or getpass('Mot de passe :')

    h = CreditAgricoleParser()
    
    for account in h.connect_and_get_balance(username, password):
        print u'%(name)s [%(number)s] : %(balance)s €' % account
