#-*- coding: utf-8 -*-
u"""Функции для удобного построения нужных типов графиков
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.font_manager as fm
fpath = 'static/css/times.ttf'
prop = fm.FontProperties(size='small',fname=fpath)

from matplotlib import pyplot


def pie_chart(values, labels, filepath):
    u'''
    values - список значений
    labels - список наименований
    filepath - путь для сохранения изображения
    '''
    pyplot.figure(1, figsize=(5, 4))
    axes_left = 0.1
    axes_bottom = 0.4
    axes_width = 0.7
    axes_height = 0.6
    explode = [0.05] * len(values)
    pyplot.axes([axes_left, axes_bottom, axes_width, axes_height])
    pyplot.pie(values, labels=[u'%s%%' % value for value in values], explode=explode)
    pyplot.legend([u'%s, %s%%' % (labels[i], values[i]) for i in xrange(len(values))], loc=(0,-0.6), prop=prop)
    pyplot.savefig(filepath, block=True)
    pyplot.close('all')



def multi_bar_chart(lefts, heights, filepath, series_x, xticks, yticks=None, xlabel=u'', ylabel=u'', title=u'', legend_labels=None, width=0.2, bar_labels=False):
    u'''
    lefts - список значений
    heights - список наименований
    filepath - путь для сохранения изображения
    series_x - количество серий
    xticks - подписи к оси Х
    yticks - подписи к оси У
    xlabel - ось Х
    ylabel - ось У
    title - заголовок графика
    legend_labels - tuple наименований серий
    width - ширина столбца
    '''
    title_kwargs = {
        'fontsize': 'small',
        'verticalalignment': 'bottom',
        'horizontalalignment': 'center'
    }

    pyplot.figure(1, figsize=(10, 5))
    axes_left = 0.1
    axes_bottom = 0.1
    axes_width = 0.5
    axes_height = 0.8
    pyplot.axes([axes_left, axes_bottom, axes_width, axes_height])
    rects = [0] * series_x
    height_maxes = [max(height) for height in heights]
    ylim_max = max(height_maxes)
    ylim_max += 0.1 * ylim_max
    for index in xrange(series_x):
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']
        colors = colors[:series_x]
        if colors:
            rects[index] = pyplot.bar(left=[l + index*width for l in lefts[index]], height=heights[index], width=width, color=colors[index], align='center')
        else:
            rects[index] = pyplot.bar(left=[l + index*width for l in lefts[index]], height=heights[index], width=width, align='center')
        pyplot.xticks(lefts[index] + width/2.0, xticks)
        if bar_labels:
            for i in xrange(len(lefts[index])):
                if heights[index][i]:
                    pyplot.text(lefts[index][i] + index*width, 1.04 * heights[index][i], heights[index][i], ha='center', va='bottom')
        if yticks:
            pyplot.yticks(yticks)

        pyplot.title(title, title_kwargs, fontproperties=prop)
        pyplot.xlabel(xlabel, fontproperties=prop)
        pyplot.ylabel(ylabel, fontproperties=prop)
        pyplot.xlim([-0.5, 5])
        pyplot.ylim([0, ylim_max])



    if legend_labels:
        legend_rects = (rect[0] for rect in rects)
        pyplot.legend(legend_rects, legend_labels, fancybox=True, bbox_to_anchor=(1.01, 1), borderaxespad=0., loc=2, prop=prop)
    pyplot.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
    pyplot.savefig(filepath, block=True)
    pyplot.close('all')
