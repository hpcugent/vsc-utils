#the vsc/utils namespace is used in different folders along the system
#so explicitly declare this is also the vsc/utils namespace
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
