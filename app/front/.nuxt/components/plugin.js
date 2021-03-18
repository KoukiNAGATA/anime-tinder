import Vue from 'vue'

const components = {
  LoginButton: () => import('../../components/LoginButton.vue' /* webpackChunkName: "components/login-button" */).then(c => c.default || c),
  NavSideBar: () => import('../../components/NavSideBar.vue' /* webpackChunkName: "components/nav-side-bar" */).then(c => c.default || c),
  TheResultAnimeInfo: () => import('../../components/TheResultAnimeInfo.vue' /* webpackChunkName: "components/the-result-anime-info" */).then(c => c.default || c),
  TheResultTextBox: () => import('../../components/TheResultTextBox.vue' /* webpackChunkName: "components/the-result-text-box" */).then(c => c.default || c)
}

for (const name in components) {
  Vue.component(name, components[name])
  Vue.component('Lazy' + name, components[name])
}
