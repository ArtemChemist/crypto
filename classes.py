import os

class Base:

    def __init__(self, param_base = 'Base'):
        self.param_base = param_base
    
    def method_base(self):
        print(self.param_base)

class Asset_local(Base):

    def __init__(self, param_local = 'Loc'):
        super().__init__()
        self.param = param_local
    
    def method_local(self):
        print(self.param)

class Asset_lambda(Base):

    def __init__(self, param_lambda = 'Lambda'):
        super().__init__()
        self.param = param_lambda
    
    def method_lambda(self):
        print(self.param)

