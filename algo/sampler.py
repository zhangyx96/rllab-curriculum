import zmq
import pickle
import cloudpickle
from optparse import OptionParser


def launch_sampler(gen_sampler):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    parser = OptionParser()
    parser.add_option("-p", "--port", dest="port",
                      help="Port to bind the socket on")
    (options, args) = parser.parse_args()
    socket.connect("tcp://localhost:%s" % options.port)
    socket.send('ack')
    message = socket.recv()
    socket.send('ack')
    with gen_sampler(message) as sampler:
        while True:
            message = pickle.loads(socket.recv())
            ret = sampler.collect_samples(*message)
            while True:
                try:
                    socket.send(cloudpickle.dumps(ret))
                    break
                except MemoryError:
                    print 'Memory error. Retrying...'
                    next
