from typing import Any, List, Union, Optional
import time
import gym
import numpy as np
from ding.envs import BaseEnv, BaseEnvTimestep, BaseEnvInfo
from ding.envs.common.env_element import EnvElement, EnvElementInfo
from ding.torch_utils import to_ndarray, to_list
from ding.utils import ENV_REGISTRY


@ENV_REGISTRY.register('coinrun')
class CoinRunEnv(BaseEnv):
    config = dict(
        control_level = True,
        start_level = 0,
        num_levels = 0,
    )
    def __init__(self, cfg: dict) -> None:
        self._cfg = cfg
        self._seed = 0
        self._init_flag = False
        self._observation_space = gym.spaces.Box(
            low=np.zeros(shape=(3, 64, 64)),
            high=np.ones(shape=(3, 64, 64)) * 255,
            shape=(3, 64, 64),
            dtype=np.float32
        )
        
        self._action_space = gym.spaces.Discrete(15)

        self._reward_space = gym.spaces.Box(low=float("-inf"), high=float("inf"), shape=(1, ), dtype=np.float32)
        self._control_level = self._cfg.control_level
        self._start_level = self._cfg.start_level
        self._num_levels = self._cfg.num_levels

    def reset(self) -> np.ndarray:
        if not self._init_flag:
            if self._control_level:
                self._env = gym.make('procgen:procgen-coinrun-v0', start_level=self._start_level, num_levels=self._num_levels)
            else:
                self._env = gym.make('procgen:procgen-coinrun-v0', start_level=0, num_levels=1)
            self._init_flag = True
        if hasattr(self, '_seed') and hasattr(self, '_dynamic_seed') and self._dynamic_seed:
            np_seed = 100 * np.random.randint(1, 1000)
            self._env.close()
            if self._control_level:
                self._env = gym.make('procgen:procgen-coinrun-v0', start_level=self._start_level, num_levels=self._num_levels)
            else:
                self._env = gym.make('procgen:procgen-coinrun-v0', start_level=self._seed + np_seed, num_levels=1)
        elif hasattr(self, '_seed'):
            self._env.close()
            if self._control_level:
                self._env = gym.make('procgen:procgen-coinrun-v0', start_level=self._start_level, num_levels=self._num_levels)
            else:
                self._env = gym.make('procgen:procgen-coinrun-v0', start_level=self._seed, num_levels=1)
        self._final_eval_reward = 0
        obs = self._env.reset()
        obs = to_ndarray(obs)
        obs = np.transpose(obs, (2, 0, 1))
        obs = obs.astype(np.float32)
        return obs

    def close(self) -> None:
        if self._init_flag:
            self._env.close()
        self._init_flag = False

    def seed(self, seed: int, dynamic_seed: bool = True) -> None:
        self._seed = seed
        self._dynamic_seed = dynamic_seed
        np.random.seed(self._seed)

    def step(self, action: np.ndarray) -> BaseEnvTimestep:
        assert isinstance(action, np.ndarray), type(action)
        if action.shape == (1, ):
            action = action.squeeze()  # 0-dim array
        obs, rew, done, info = self._env.step(action)
        self._final_eval_reward += rew
        if done:
            info['final_eval_reward'] = self._final_eval_reward
        obs = to_ndarray(obs)
        obs = np.transpose(obs, (2, 0, 1))
        obs = obs.astype(np.float32)
        rew = to_ndarray([rew])  # wrapped to be transfered to a array with shape (1,)
        rew = rew.astype(np.float32)
        return BaseEnvTimestep(obs, rew, bool(done), info)

    @property
    def observation_space(self) -> gym.spaces.Space:
        return self._observation_space

    @property
    def action_space(self) -> gym.spaces.Space:
        return self._action_space

    @property
    def reward_space(self) -> gym.spaces.Space:
        return self._reward_space

    def __repr__(self) -> str:
        return "DI-engine CoinRun Env"

    def enable_save_replay(self, replay_path: Optional[str] = None) -> None:
        if replay_path is None:
            replay_path = './video'
        self._replay_path = replay_path
        self._env = gym.wrappers.Monitor(
            self._env, self._replay_path, video_callable=lambda episode_id: True, force=True
        )
