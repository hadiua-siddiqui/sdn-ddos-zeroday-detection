from mininet.topo import Topo

class FypTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        for name in ('h1', 'h2', 'h3'):
            self.addLink(self.addHost(name), s1)
        for name in ('h4', 'h5'):
            self.addLink(self.addHost(name), s2)
        self.addLink(s1, s2)

topos = {'fyp': FypTopo}
