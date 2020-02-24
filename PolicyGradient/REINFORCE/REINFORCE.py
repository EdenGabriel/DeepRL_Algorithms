import torch
import torch.optim as optim
from torch.distributions import Categorical
from torch.utils.tensorboard import SummaryWriter

from PolicyGradient.Models.Reinforce_policy import Policy
from Utils.env_util import get_env_space


class REINFORCE:
    def __init__(self,
                 num_states,
                 num_actions,
                 learning_rate=0.02,
                 gamma=0.995,
                 eps=torch.finfo(torch.float32).eps,
                 enable_gpu=False
                 ):

        if enable_gpu:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device("cpu")

        self.policy = Policy(num_states, num_actions).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=learning_rate)
        self.gamma = gamma
        self.eps = eps

        self.rewards = []  # 记录轨迹的每个 time step 对应的及时回报 r_t
        self.log_probs = []  # 记录轨迹的每个 time step 对应的 log_probability
        self.cum_rewards = []  # 记录轨迹的每个 time step 对应的 累计回报 G_t

    def calc_cumulative_rewards(self):
        R = 0.0
        for r in self.rewards[::-1]:
            R = r + self.gamma * R
            self.cum_rewards.insert(0, R)

    def choose_action(self, state):
        state = torch.tensor(state).unsqueeze(0).to(self.device).float()
        probs = self.policy(state)

        # 对action进行采样,并计算log probability
        m = Categorical(probs)
        action = m.sample()
        log_prob = m.log_prob(action)
        self.log_probs.append(log_prob)
        return action.item()

    def update_episode(self):
        self.calc_cumulative_rewards()

        # Normalize reward
        rewards = torch.tensor(self.cum_rewards).to(self.device)
        rewards = (rewards - rewards.mean()) / (rewards.std() + self.eps)
        # 梯度上升更新策略参数

        loss = - (torch.cat(self.log_probs) * rewards).mean()

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.rewards.clear()
        self.log_probs.clear()
        self.cum_rewards.clear()


if __name__ == '__main__':
    env_id = 'MountainCar-v0'
    alg_id = 'REINFORCE'
    env, num_states, num_actions = get_env_space(env_id)

    agent = REINFORCE(num_states, num_actions, enable_gpu=True)
    episodes = 1000

    writer = SummaryWriter()
    iterations_ = []
    rewards_ = []

    # 迭代所有episodes进行采样
    for i in range(episodes):
        # 当前episode开始
        state = env.reset()
        episode_reward = 0

        for t in range(10000):
            env.render()
            action = agent.choose_action(state)
            state, reward, done, info = env.step(action)

            episode_reward += reward
            agent.rewards.append(reward)

            # 当前episode　结束
            if done:
                break

        iterations_.append(i)
        rewards_.append(episode_reward)

        writer.add_scalar(alg_id, episode_reward, i)
        print("Episode: {} , the episode reward is {}".format(i, round(episode_reward, 3)))

        agent.update_episode()

    env.close()
