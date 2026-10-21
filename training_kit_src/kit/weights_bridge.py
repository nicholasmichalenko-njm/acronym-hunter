"""Move trained weights between PaddlePaddle versions without pickle/NumPy-version coupling.
  to-npz   <weights prefix> <out.npz>     (run in the training Python)
  from-npz <in.npz> <weights prefix>      (run in the export Python; writes <prefix>.pdparams)"""
import sys
import numpy as np
import paddle
mode, src, dst = sys.argv[1:4]
if mode == "to-npz":
    state = paddle.load(src + ".pdparams")
    np.savez(dst, **{k: (v.numpy() if hasattr(v, "numpy") else np.asarray(v)) for k, v in state.items()})
    print(f"wrote {len(state)} tensors to {dst}")
elif mode == "from-npz":
    data = np.load(src)
    paddle.save({k: data[k] for k in data.files}, dst + ".pdparams")
    print(f"wrote {len(data.files)} tensors to {dst}.pdparams")
