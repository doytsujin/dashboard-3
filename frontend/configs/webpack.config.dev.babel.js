import path from 'path';
import webpack from 'webpack';
import merge from 'webpack-merge';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import common from './webpack.config.babel';

const src = path.resolve(__dirname, '../src');
const dist_dev = path.resolve(__dirname, '../dist_dev');


const devConfig = {
  mode: 'development',

  output: {
    path: dist_dev,
    publicPath: '/dist_dev/'
  },

  devServer: {
    historyApiFallback: { index: '/dist_dev/index.html' },
    contentBase: dist_dev,
    inline: true,
    port: 8080,
    host: "0.0.0.0",
    progress: true
  },

  plugins: [
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: JSON.stringify('development'),
        API_HOST: JSON.stringify(process.env.API_HOST || 'http://localhost'),
        API_PORT: JSON.stringify(process.env.API_PORT || '18080')
      }
    }),
    new HtmlWebpackPlugin({
      filename: 'index.html',
      title: 'dashboard-frontend-dev',
      template: `${src}/index.html`,
    }),
  ]
};

export default merge(common, devConfig);
