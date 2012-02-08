import configparser

class Settings(object):
    
    def __init__(self, configfile):    
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(configfile)
    
    def load(self, section, opts):
        try:
            for key in opts:
                try:
                    setattr(self, key, self.config.get(section, key))
                except configparser.NoOptionError:
                    setattr(self, key, self.config.get('default', key))

        except configparser.NoSectionError:
            print('The section "%s" does not exist' % section)
        except configparser.NoOptionError:
            print('The value for "%s" is missing' % key)
        else:
            return True
        return False