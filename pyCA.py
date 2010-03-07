#! /usr/bin/env python
# -*- coding: utf-8 -*-

from urllib import urlencode
import urllib2
import cookielib
import re
try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from sys import exit
    print "Impossible d'importer le module beautilfulSoup. Vérifiez son installation."
    exit()


class CreditAgricoleParser():
    "Récupère des informations concernant un compte Credit Agricole"
    
    AUTH_FORM_TARGET = 'https://www.cr867-comete-g2-enligne.credit-agricole.fr/stb/entreeBam'

    def __init__(self):
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
        
    
    
    def get_page(self, url, post_data=None):
        if post_data is None:
            return self.opener.open(url).read()
        else:
            return self.opener.open(url, urlencode(post_data)).read()

    def get_login_page(self):
        """Renvoie le code source HTML de la page contenant le formulaire d'authentification."""
        post_data= {
            'TOP_ORIGINE':'V',
            'vitrine':'0',
            'largeur_ecran':'800',
            'hauteur_ecran':'600',
            'origine':'vitrine',
            'situationTravail':'BANQUAIRE',
            'canal':'WEB',
            'typeAuthentification':'CLIC_ALLER',
            'urlOrigine':'http://www.ca-norddefrance.fr'
        }
        return self.get_page(self.AUTH_FORM_TARGET, post_data)
    
    
    def get_trans_dict(self, login_page_source):
        """La page d'authentification utilise une grille 5x5 dans laquelle les chiffres 0-9 sont placés aléatoirement.
        Quand on clique sur un des chiffres, le systeme enregistre la position du clic dans la grille.
        Les cases sont numérotées ainsi:
        1  2  3  4  5
        6  7  8  9  10
        11 12 13 14 15
        16 17 18 19 20
        21 22 23 24 25
        
        Coté HTML, voici le balisage d'une case:
        <td class="case" onClick="clicPosition('03'); " onMouseOver="this.className='rollover';StatusMessage(true, statusclavnum);return true" onMouseOut="this.className='case';StatusMessage( false )"><a tabindex=4 href="javascript:raf()" style="font-family:Arial, sans-serif;font-size:14px;color:#CA1111;font-weight:bold;text-decoration:none;">&nbsp;&nbsp;4&nbsp;&nbsp;</a></td>
        
        
        Cette méthode renvoie un dictionnaire dont les clés sont les chiffres de 1 a 9 et les valeurs leur traduction en termes de position dans la grille.
        """
        rxp = re.compile(r"clicPosition\('(\d{2})'\);")
        cases = BeautifulSoup(login_page_source).findAll('td', attrs={'class': 'case', 'onclick': True})
        return dict([(case.a.string.replace('&nbsp;', ' ').strip(), rxp.match(case['onclick']).group(1)) for case in cases])


    def get_post_data_for_login(self, login_page_source, account_number, password):
        """Cette méthode se charge de renvoyer un dictionanire correspondant aux champs qui doivent etre envoyés pour que l'authentification soit positive.
        Il faut en particulier "traduire" le mot de passe a 6 chiffres (cf la méthode get_trans_dict)."""
        soup = BeautifulSoup(login_page_source)
        form = soup.findAll('form', attrs={'name':'formulaire'})[0]
        
        trans_dict = self.get_trans_dict(login_page_source)
        
        post_data = dict([(e['name'], e.get('value')) for e in form.findAll('input')])
        
        post_data.update({
            'CCCRYC2': '0'*6,
            'CCPTE': account_number,
            'CCCRYC': ','.join([trans_dict.get(e) for e in password])
        })
        
        return post_data

    def get_landing_page(self, login_post_data):
        """Retourne le code source de la page d'accueil une fois l'utilisateur authentifié."""
        return self.get_page(self.AUTH_FORM_TARGET, login_post_data)
    

    def get_balance(self, landing_page_source):
        """Renvoie une liste de tous les comptes avec pour chacun le nom du compte, son numéro ainsi que le solde."""
        comment_begin = '<!-----  DEBUT zone enteteTech  ---->'
        comment_end = '<!-----  FIN zone enteteTech  ---->'
        
        # The following line cuts out a piece of the html that makes BeautifulSoup choke (because of some ugly inline javascript)
        landing_page_source = landing_page_source[:landing_page_source.find(comment_begin)] + landing_page_source[landing_page_source.find(comment_end)+len(comment_end):]
        
        soup = BeautifulSoup(landing_page_source)
        def format_data(e):
            return {
                'name': e.findAll('a', attrs={'class':'libelle5'})[0].string.strip(),
                'number': e.findAll('a', attrs={'class':'libelle3'})[0].string.strip(),
                'balance': float(e.findAll('a', attrs={'class':'montant3'})[0].string.strip().replace(',', '.').replace(' ', '')),
            }
        return [format_data(e) for e in soup.findAll('tr', attrs={'class':('colcellignepaire', 'colcelligneimpaire')})]
    
    
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
    p.add_option('-u', '--username', help="Le numéro du compte utilisé pour se connecter", dest='username')
    p.add_option('-p', '--password', help="Le mot de passe à 6 chiffres", dest='password')
    options, args = p.parse_args()
    
    username = options.username or raw_input('Numéro de compte :')
    password = options.password or getpass('Mot de passe :')

    h = CreditAgricoleParser()
    
    for account in h.connect_and_get_balance(username, password):
        print u'%(name)s [%(number)s] : %(balance)s €' % account 
