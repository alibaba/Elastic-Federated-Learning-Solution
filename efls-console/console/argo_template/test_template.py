# -*- coding: utf8 -*-

import kfp


def flip_coin():
    return kfp.dsl.ContainerOp(
        name='Flip a coin',
        image='python:alpine3.6',
        command=['python', '-c', """
import random
res = "heads" if random.randint(0, 1) == 0 else "tails"
with open('/output', 'w') as f:
    f.write(res)
        """],
        file_outputs={'output': '/output'}
    )


def end():
    return kfp.dsl.ContainerOp(name='End', image="alpine:3.6", command=["sh", "-c", 'echo "Flip coin ends"'])


def heads():
    return kfp.dsl.ContainerOp(name='Heads', image="alpine:3.6", command=["sh", "-c", 'echo "it was heads"'])


def tails():
    return kfp.dsl.ContainerOp(name='Tails', image="alpine:3.6", command=["sh", "-c", 'echo "it was tails"'])


@kfp.dsl.pipeline(name='Coin-flip', description='Flip a coin')
def coin_flip_pipeline():
    flip_op = flip_coin()
    result_op = None
    with kfp.dsl.Condition(flip_op.output == 'heads'):
        result_op = heads()
    with kfp.dsl.Condition(flip_op.output == 'tails'):
        result_op = tails()
    end_op = end()
    end_op.after(result_op)


def main():
    kfp.compiler.Compiler().compile(coin_flip_pipeline, __file__ + ".yaml")


if __name__ == '__main__':
    main()
