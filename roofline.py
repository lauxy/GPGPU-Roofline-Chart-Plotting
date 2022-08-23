
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

font = {'size' : 15}
plt.rc('font', **font)

colors = ['tab:blue','tab:orange','tab:green','tab:red','tab:purple','tab:brown','tab:pink','tab:gray','tab:olive','tab:cyan']
styles = ['o','s','v','^','D',">","<","*","h","H","+","1","2","3","4","8","p","d","|","_",".",","]

markersize = 10
markerwidth = 2
maxchar = 25

# function format: roofline(tag, dfs, options)
# def roofline(filename, FLOPS, AIHBM, AIL2=None, AIL1=None, LABELS=None, flag='HBM'):
def roofline(filename, dfmetric, options, exe_list):

    FLOPS = dfmetric['Achieved All GLOPS'].tolist()
    if not FLOPS:
        print('FLOPS can not be empty!')
        return
    elif max(FLOPS)==0:
        print('FLOPS are all 0s!')
        return
    if 'HBM' in options['mem_options']:
        AIHBM = dfmetric['AI HBM'].tolist()
        if not AIHBM:
            print('AIHBM can not all be empty!')
            return
    if 'L1' in options['mem_options']:
        AIL1  = dfmetric['AI L1'].tolist()
        if not AIL1:
            print('AIL1 can not all be empty!')
            return
    if 'L2' in options['mem_options']:
        AIL2  = dfmetric['AI L2'].tolist()
        if not AIL2:
            print('AIL2 can not all be empty!')
            return

    PeakHBM = dfmetric['Peak HBM'].tolist()
    PeakL1  = dfmetric['Peak L1'].tolist()
    PeakL2  = dfmetric['Peak L2'].tolist()
    PeakDP  = dfmetric['Peak DP'].tolist()
    PeakSP  = dfmetric['Peak SP'].tolist()
    PeakHP  = dfmetric['Peak HP'].tolist()
    PeakTensor  = dfmetric['Peak TC'].tolist()

    # Theoretical Peak TFLOPS
    # PeakDP  = [9.7]
    # PeakSP  = [19.5]
    # PeakHP  = [79]
    # PeakTensor  = [312]

    if len(AIHBM) == len(exe_list):
        LABELS = [x[:maxchar] for x in exe_list]
    else:
        LABELS = [x[:maxchar] for x in dfmetric.index.tolist()]

    # memory related roofline metrics and compute related roofline metrics
    memRoofs = []
    for item in options['mem_options'].split(','):
        memRoofs.append((item, eval('Peak'+item)[0]))
    cmpRoofs = []
    for item in options['alu_options'].split(','):
        cmpRoofs.append((item, eval('Peak'+item)[0]))

    fig = plt.figure(1,figsize=(10.67,6.6))
    plt.clf()
    ax = fig.gca()
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Arithmetic Intensity [FLOPs/Byte]')
    ax.set_ylabel('Performance [GFLOP/sec]')

    nx   = 10000
    xmin = -3
    xmax = 4
    ymin = 1
    ymax = 2000000

    ax.set_xlim(10**xmin, 10**xmax)  # x axis range
    ax.set_ylim(ymin, ymax)          # y axis range

    ixx = int(nx*0.02)
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    scomp_x_elbow  = []
    scomp_ix_elbow = []
    smem_x_elbow   = []
    smem_ix_elbow  = []

    x = np.logspace(xmin,xmax,nx)
    for roof in cmpRoofs:
        for ix in range(1,nx):
            if float(memRoofs[0][1] * x[ix]) >= roof[1]*1024 and (memRoofs[0][1] * x[ix-1]) < roof[1]*1024:
                scomp_x_elbow.append(x[ix-1])
                scomp_ix_elbow.append(ix-1)
                break

    for roof in memRoofs:
        for ix in range(1,nx):
            if (cmpRoofs[0][1]*1024 <= roof[1] * x[ix] and cmpRoofs[0][1]*1024 > roof[1] * x[ix-1]):
                smem_x_elbow.append(x[ix-1])
                smem_ix_elbow.append(ix-1)
                break
    
    
    for i in range(len(cmpRoofs)):
        roof = cmpRoofs[i][1]*1024   # TFLOPS * 1024 = GFLOPS
        y = np.ones(len(x)) * roof
        ax.plot(x[scomp_ix_elbow[i]:],y[scomp_ix_elbow[i]:],c='k',ls='-',lw='2')

    for i in range(len(memRoofs)):
        roof = memRoofs[i][1]
        y = x * roof
        ax.plot(x[:smem_ix_elbow[i]+1],y[:smem_ix_elbow[i]+1],c='k',ls='-',lw='2')

    for i in range(len(AIHBM)):
        print('marker '+str(i)+': '+str(dfmetric.index.tolist()[i]))
        if 'L1' in options['mem_options']:
            ax.plot(float(AIL1[i]),float(FLOPS[i]),c=colors[i%10],marker=styles[0],\
                    linestyle='None',ms=markersize,markerfacecolor='none',\
                    markeredgewidth=markerwidth,label=LABELS[i] if LABELS else "unknown")
        if 'L2' in options['mem_options']:
            ax.plot(float(AIL2[i]),float(FLOPS[i]),c=colors[i%10],marker=styles[1],\
                    linestyle='None',ms=markersize,markerfacecolor='none',\
                    markeredgewidth=markerwidth,label=LABELS[i] if LABELS else "unknown")
        if 'HBM' in options['mem_options']:
            ax.plot(float(AIHBM[i]),float(FLOPS[i]),c=colors[i%10],marker=styles[2],\
                    linestyle='None',ms=markersize,markerfacecolor='none',\
                    markeredgewidth=markerwidth,label=LABELS[i] if LABELS else "unknown")

    marker_handles = []  

    for i in range(len(memRoofs)):
        marker_styles_id = 0 if memRoofs[i][0]=='L1' else 1 if memRoofs[i][0]=='L2' else 2  
        marker_handles.append(ax.plot([],[],c='k',marker=styles[marker_styles_id],linestyle='None',ms=markersize,\
                                markerfacecolor='none',markeredgewidth=markerwidth,label=memRoofs[i][0])[0])            


    for roof in cmpRoofs:
        ax.text(x[-ixx],roof[1]*1024,
              roof[0] + ': ' + '{0:.1f}'.format(roof[1]) + ' TFLOP/s',
              horizontalalignment='right',
              verticalalignment='bottom')

    for roof in memRoofs:
        ang = np.arctan(np.log10(xlim[1]/xlim[0]) / np.log10(ylim[1]/ylim[0])
                                   * fig.get_size_inches()[1]/fig.get_size_inches()[0] )
        if x[ixx]*roof[1] >ymin:
            ax.text(x[ixx],x[ixx]*roof[1]*(1+0.25*np.sin(ang)**2),
              roof[0] + ': ' + '{0:.1f}'.format(float(roof[1])) + ' GB/s',
              horizontalalignment='left',
              verticalalignment='bottom',
              rotation=180/np.pi*ang)
        else:
            ymin_ix_elbow=list()
            ymin_x_elbow=list()
            for ix in range(1,nx):
                if (ymin <= roof[1] * x[ix] and ymin > roof[1] * x[ix-1]):
                    ymin_x_elbow.append(x[ix-1])
                    ymin_ix_elbow.append(ix-1)
                    break
            ax.text(x[ixx+ymin_ix_elbow[0]],x[ixx+ymin_ix_elbow[0]]*roof[1]*(1+0.25*np.sin(ang)**2),
              roof[0] + ': ' + '{0:.1f}'.format(float(roof[1])) + ' GB/s',
              horizontalalignment='left',
              verticalalignment='bottom',
              rotation=180/np.pi*ang)


        
    leg1 = plt.legend(handles = marker_handles,loc='lower right', ncol=3, bbox_to_anchor = (1,0))
    ax.add_artist(leg1)

    patch_handles = list()
    for i in range(0,len(AIHBM)):
        if FLOPS[i] > 0:
            patch_handles.append(mpatches.Patch(color=colors[i%10],label = LABELS[i] if LABELS else "unknown"))

    plt.legend(handles = patch_handles,loc=4,ncol=1,bbox_to_anchor = (1,0.1),scatterpoints = 1)

    # ax.text(xlim[0]*1.1,ylim[1]/1.1, '-'.join([filename, options['mem_options'].replace(',','_')]), horizontalalignment='left',verticalalignment='top')
    # plt.title('-'.join([filename,flag]))
    plt.title(options['rfl_name'])

    # plt.savefig('_'.join([filename, options['mem_options'].replace(',','_')])+'.png')
    plt.savefig(options['rfl_name']+'.png')

#    plt.show()
